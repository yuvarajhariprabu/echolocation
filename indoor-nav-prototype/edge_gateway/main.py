"""
main.py — Edge Gateway Orchestrator

Starts all subsystems and runs the main event loop:
  1. BLE Gateway (connects to sensor node + CAM node)
  2. Fusion Engine (sensor + vision → fused obstacle)
  3. Grid Updater (fused obstacle → tile grid)
  4. A* Planning (tile grid → path)
  5. Decision Engine (fused obstacle + path → guidance cues)
  6. Audio + Haptic output
  7. WebSocket map stream (tile grid → browser UI)

Usage:
    python -m edge_gateway.main
    or
    python edge_gateway/main.py

Requirements:
    pip install bleak websockets pyttsx3 numpy pyyaml
"""

import asyncio
import logging
import yaml
import math
import time
from pathlib import Path

# Load class definitions ONCE at module level — not inside hot loop
_CLASS_DEF_PATH = Path(__file__).parent.parent / "aiml" / "shared" / "class_definitions.yaml"
with open(_CLASS_DEF_PATH) as _f:
    _class_defs = yaml.safe_load(_f)
SENSOR_CLASS_NAMES = {c["index"]: c["name"] for c in _class_defs["sensor_classes"]}

from .fusion.event_schema   import SensorEvent, VisionEvent, FusedObstacle
from .fusion.fusion_engine  import FusionEngine
from .mapping.tile_grid     import TileGrid
from .mapping.localization  import Localization
from .mapping.grid_updater  import GridUpdater
from .planning.astar        import astar
from .planning.replanning_trigger import ReplanningTrigger
from .guidance.decision_engine import DecisionEngine
from .guidance.audio_feedback  import AudioFeedback
from .guidance.haptic_feedback import HapticFeedback
from .comms.ble_gateway     import BLEGateway
from .comms.map_stream      import MapStream

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config" / "gateway_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)


class Gateway:

    def __init__(self):
        self.grid       = TileGrid(
            width=cfg["grid"]["width"],
            height=cfg["grid"]["height"],
            tile_size_cm=cfg["grid"]["tile_size_cm"],
            dynamic_decay_rate=cfg["grid"]["dynamic_decay_rate"],
        )
        self.localization    = Localization(self.grid)
        self.grid_updater    = GridUpdater(self.grid)
        self.fusion_engine   = FusionEngine()
        self.decision_engine = DecisionEngine()
        self.replan_trigger  = ReplanningTrigger()
        self.audio           = AudioFeedback()
        self.haptic          = HapticFeedback(simulate=cfg.get("simulate_haptic", True))
        self.map_stream      = MapStream(
            port=cfg["map_stream"]["port"],
            on_goal_callback=self._on_goal_received,
        )
        self.ble_gateway = BLEGateway(
            on_sensor_event=self._on_sensor_event_threadsafe,
            on_vision_event=self._on_vision_event_threadsafe,
        )
        self._current_path = []
        self._goal_tile    = None
        self._last_fused: FusedObstacle = None
        self._loop: asyncio.AbstractEventLoop = None  # set in run()

    # ── Thread-safe BLE callbacks ─────────────────────────────────────────
    # bleak calls these from its own background thread. We must NOT call any
    # asyncio primitives or shared state directly here.
    # call_soon_threadsafe() safely schedules work back on the event loop thread.

    def _on_sensor_event_threadsafe(self, ev: SensorEvent):
        """Called from bleak's background thread — dispatch to event loop."""
        if self._loop:
            self._loop.call_soon_threadsafe(self._on_sensor_event, ev)

    def _on_vision_event_threadsafe(self, ev: VisionEvent):
        if self._loop:
            self._loop.call_soon_threadsafe(self._on_vision_event, ev)

    def _on_sensor_event(self, ev: SensorEvent):
        """Runs on event loop thread — safe to access all state."""
        fused = self.fusion_engine.on_sensor_event(ev)
        self._process_fused(fused, ev)

    def _on_vision_event(self, ev: VisionEvent):
        fused = self.fusion_engine.on_vision_event(ev)
        if fused:
            self._process_fused(fused, None)

    def _process_fused(self, fused: FusedObstacle, sensor_ev: SensorEvent):
        # Update position from IMU
        if sensor_ev:
            self.localization.update(sensor_ev)

        # Update grid
        self.grid_updater.update(fused)
        self.grid.decay_dynamic()

        # Replan if needed
        if self._goal_tile and self.replan_trigger.should_replan(fused, self._current_path, self.grid):
            self._replan()

        # Guidance
        cue = self.decision_engine.decide(fused, self._current_path, self.grid)

        # Fast-path haptic (design rule #1: never wait on audio)
        self.haptic.set(
            front=cue.haptic_front,
            left=cue.haptic_left,
            right=cue.haptic_right,
        )

        # Special patterns
        cls_name = SENSOR_CLASS_NAMES.get(fused.fused_class, "")
        if cls_name == "dropoff_edge":
            self.haptic.pattern_dropoff()
        elif cue.is_urgent and fused.is_caution:
            self.haptic.pattern_caution()

        # Audio (non-blocking — queued)
        self.audio.speak(cue.audio_text, urgent=cue.is_urgent)

        self._last_fused = fused

    def _on_goal_received(self, tx: int, ty: int):
        log.info(f"[Gateway] Goal received: tile ({tx}, {ty})")
        self._goal_tile = (tx, ty)
        self._replan()

    def _replan(self):
        if not self._goal_tile:
            return
        path = astar(self.grid, *self._goal_tile)
        if path:
            self._current_path = path
            log.info(f"[Gateway] Path found: {len(path)} tiles")
        else:
            log.warning("[Gateway] No path found to goal")
            self._current_path = []

    async def _map_broadcast_loop(self):
        """Periodically push grid state to map viewer UI."""
        interval = cfg["map_stream"].get("update_interval_s", 0.2)
        while True:
            await self.map_stream.broadcast_grid(self.grid.to_dict())
            if self._current_path:
                await self.map_stream.broadcast_path(self._current_path)
            await asyncio.sleep(interval)

    async def run(self):
        log.info("[Gateway] Starting BlindNav Edge Gateway...")
        self._loop = asyncio.get_running_loop()  # capture for thread-safe callbacks
        self.audio.start()

        await self.map_stream.start()

        # Run both background tasks; if either raises, the exception propagates
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._map_broadcast_loop(), name="map_broadcast")
            tg.create_task(self.ble_gateway.run(),     name="ble_gateway")
            log.info("[Gateway] All systems running. Waiting for BLE connections...")


def main():
    asyncio.run(Gateway().run())


if __name__ == "__main__":
    main()
