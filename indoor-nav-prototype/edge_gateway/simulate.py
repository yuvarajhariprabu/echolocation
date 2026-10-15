"""
simulate.py — Hardware-Free Simulation Mode

Runs the complete BlindNav pipeline WITHOUT any physical hardware.
Generates realistic fake sensor + vision events and feeds them into
the gateway's fusion engine.

The map viewer (app_ui/map_viewer/index.html) connects normally via WebSocket
and shows a live simulation of:
  - User walking through a room
  - Static obstacles (walls, chairs, tables)
  - A moving dynamic object (person) crossing the user's path
  - A* path planning updating in real time

Usage:
    cd "c:\\Users\\yuvar\\Documents\\hack 2\\indoor-nav-prototype"
    python -m edge_gateway.simulate

Then open:
    app_ui/map_viewer/index.html  in your browser
"""

import asyncio
import logging
import math
import random
import time
import yaml
from pathlib import Path

# ── Gateway imports ────────────────────────────────────────────────────────
from edge_gateway.fusion.event_schema   import SensorEvent, VisionEvent, FusedObstacle
from edge_gateway.fusion.fusion_engine  import FusionEngine
from edge_gateway.mapping.tile_grid     import TileGrid
from edge_gateway.mapping.localization  import Localization
from edge_gateway.mapping.grid_updater  import GridUpdater
from edge_gateway.planning.astar        import astar
from edge_gateway.planning.replanning_trigger import ReplanningTrigger
from edge_gateway.guidance.decision_engine    import DecisionEngine
from edge_gateway.guidance.audio_feedback     import AudioFeedback
from edge_gateway.guidance.haptic_feedback    import HapticFeedback
from edge_gateway.comms.map_stream      import MapStream

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("simulate")

CONFIG_PATH = Path(__file__).parent / "config" / "gateway_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

# ── Simulation parameters ──────────────────────────────────────────────────
TICK_HZ          = 10          # simulation ticks per second
GRID_W           = cfg["grid"]["width"]
GRID_H           = cfg["grid"]["height"]
GRID_CX          = GRID_W // 2
GRID_CY          = GRID_H // 2

# User starts at centre-left and walks right
USER_PATH = [
    (GRID_CX - 15, GRID_CY),
    (GRID_CX - 10, GRID_CY),
    (GRID_CX - 5,  GRID_CY),
    (GRID_CX,      GRID_CY),
    (GRID_CX + 5,  GRID_CY),
    (GRID_CX + 10, GRID_CY),
    (GRID_CX + 10, GRID_CY - 5),
    (GRID_CX + 10, GRID_CY - 10),
    (GRID_CX + 5,  GRID_CY - 10),
    (GRID_CX,      GRID_CY - 10),
]

# Static obstacles: (tx, ty) — furniture + walls
STATIC_OBSTACLES = [
    # Right wall section
    *[(GRID_CX + 14, y) for y in range(GRID_CY - 14, GRID_CY + 3)],
    # Table cluster
    *[(GRID_CX + 6, GRID_CY - 2), (GRID_CX + 7, GRID_CY - 2),
      (GRID_CX + 6, GRID_CY - 3), (GRID_CX + 7, GRID_CY - 3)],
    # Chair
    (GRID_CX + 2, GRID_CY + 2),
    # Doorframe
    (GRID_CX - 16, GRID_CY - 1),
    (GRID_CX - 16, GRID_CY + 1),
]

# Vision classes (index → name) for simulation
SENSOR_CLASS_NAMES = {
    0: "static_obstacle", 1: "moving_object", 2: "open_space",
    3: "dropoff_edge",    4: "approaching",   5: "receding",
    6: "crossing",        7: "user_motion",   8: "unknown",
}
VISION_CLASS_NAMES = {
    0: "person", 1: "chair", 2: "table",
    3: "door",   4: "stairs", 5: "wall", 6: "unknown_object",
}


class Simulation:

    def __init__(self):
        self.grid       = TileGrid(
            width=GRID_W, height=GRID_H,
            tile_size_cm=cfg["grid"]["tile_size_cm"],
            dynamic_decay_rate=cfg["grid"]["dynamic_decay_rate"],
        )
        self.localization    = Localization(self.grid)
        self.grid_updater    = GridUpdater(self.grid)
        self.fusion_engine   = FusionEngine()
        self.decision_engine = DecisionEngine()
        self.replan_trigger  = ReplanningTrigger()
        self.audio           = AudioFeedback()
        self.haptic          = HapticFeedback(simulate=True)
        self.map_stream      = MapStream(
            port=cfg["map_stream"]["port"],
            on_goal_callback=self._on_goal,
        )

        self._path       = []
        self._goal_tile  = USER_PATH[-1]   # auto-set goal to end of demo path
        self._tick       = 0
        self._user_wp    = 0               # current waypoint index
        self._dynamic_x  = GRID_CX + 5    # moving person X
        self._dynamic_y  = GRID_CY + 8    # moving person Y (walks upward)

        # Pre-stamp static obstacles into grid
        for (tx, ty) in STATIC_OBSTACLES:
            if 0 <= tx < GRID_W and 0 <= ty < GRID_H:
                self.grid._static[ty, tx] = 1

        # Set user start position
        self.grid.user.tile_x = USER_PATH[0][0]
        self.grid.user.tile_y = USER_PATH[0][1]

    # ── Simulation helpers ─────────────────────────────────────────────────

    def _nearest_static_cm(self, tx, ty) -> float:
        """Distance in cm from (tx,ty) to the nearest static obstacle ahead."""
        best = 400.0
        tile_cm = cfg["grid"]["tile_size_cm"]
        for (ox, oy) in STATIC_OBSTACLES:
            if oy == ty and ox > tx:   # same row, ahead
                d = (ox - tx) * tile_cm
                if d < best:
                    best = d
        return best

    def _fake_sensor_event(self) -> SensorEvent:
        """Generate a realistic sensor event for the current user position."""
        ux = self.grid.user.tile_x
        uy = self.grid.user.tile_y

        front_cm = self._nearest_static_cm(ux, uy)

        # Dynamic person nearby?
        dist_to_person = abs(ux - self._dynamic_x) + abs(uy - self._dynamic_y)
        if dist_to_person < 4:
            front_cm = min(front_cm, dist_to_person * cfg["grid"]["tile_size_cm"])

        # Add sensor noise
        front_cm += random.gauss(0, 2)
        left_cm   = random.uniform(50, 200)
        right_cm  = random.uniform(50, 200)

        # Determine class
        if front_cm < 40:
            cls_idx  = 0   # static_obstacle
            conf     = 0.88
        elif dist_to_person < 4:
            cls_idx  = 4   # approaching
            conf     = 0.80
        elif dist_to_person < 7:
            cls_idx  = 1   # moving_object
            conf     = 0.75
        else:
            cls_idx  = 2   # open_space
            conf     = 0.90

        return SensorEvent(
            ts           = time.time(),
            front_cm     = max(2.0, front_cm),
            left_cm      = left_cm,
            right_cm     = right_cm,
            floor_mm     = 15,
            yaw_rate_dps = random.gauss(0, 1),
            stationary   = False,
            class_index  = cls_idx,
            confidence   = conf,
        )

    def _fake_vision_event(self) -> VisionEvent | None:
        """Generate a vision event occasionally (camera is triggered, not always active)."""
        ux = self.grid.user.tile_x
        dist = abs(ux - self._dynamic_x) + abs(self.grid.user.tile_y - self._dynamic_y)
        if dist > 8:
            return None

        # Person detected
        return VisionEvent(
            ts         = time.time(),
            class_index= 0,      # person
            confidence = 0.82,
            grid_x     = self._dynamic_x - ux,
            grid_y     = 0,
        )

    def _advance_user(self):
        """Move user one step along the demo waypoint path."""
        if self._user_wp < len(USER_PATH) - 1:
            # Move every 0.5s (every 5 ticks at 10Hz)
            if self._tick % 5 == 0:
                self._user_wp = min(self._user_wp + 1, len(USER_PATH) - 1)

        wp = USER_PATH[self._user_wp]
        self.grid.user.tile_x = wp[0]
        self.grid.user.tile_y = wp[1]

        # Heading: angle toward next waypoint
        if self._user_wp < len(USER_PATH) - 1:
            nx, ny = USER_PATH[self._user_wp + 1]
            dx = nx - wp[0]; dy = ny - wp[1]
            self.grid.user.heading_deg = math.degrees(math.atan2(dx, -dy)) % 360

    def _advance_dynamic_person(self):
        """Move the simulated person across the user's path."""
        if self._tick % 8 == 0:
            self._dynamic_y -= 1   # person walks upward (decreasing Y)
            if self._dynamic_y < GRID_CY - 14:
                self._dynamic_y = GRID_CY + 8   # reset

        # Stamp into dynamic grid layer
        if 0 <= self._dynamic_x < GRID_W and 0 <= self._dynamic_y < GRID_H:
            self.grid._dynamic[self._dynamic_y, self._dynamic_x] = 0.85

    def _on_goal(self, tx, ty):
        log.info(f"[Sim] Goal from map viewer: ({tx}, {ty})")
        self._goal_tile = (tx, ty)
        self._replan()

    def _replan(self):
        if self._goal_tile:
            path = astar(self.grid, *self._goal_tile)
            self._path = path if path else []
            if path:
                log.info(f"[Sim] Path found: {len(path)} tiles → {self._goal_tile}")
            else:
                log.warning(f"[Sim] No path to {self._goal_tile}")

    # ── Main simulation tick ───────────────────────────────────────────────

    def tick(self):
        self._tick += 1

        self._advance_user()
        self._advance_dynamic_person()

        # Sensor event every tick
        ev = self._fake_sensor_event()
        fused = self.fusion_engine.on_sensor_event(ev)
        self.grid_updater.update(fused)
        self.grid.decay_dynamic()

        # Vision event occasionally (every ~2s)
        if self._tick % 20 == 0:
            vev = self._fake_vision_event()
            if vev:
                fused2 = self.fusion_engine.on_vision_event(vev)
                if fused2:
                    self.grid_updater.update(fused2)

        # Replan every 2s or when triggered
        if self._tick % 20 == 0:
            self._replan()

        # Guidance
        cue = self.decision_engine.decide(fused, self._path, self.grid)
        self.haptic.set(cue.haptic_front, cue.haptic_left, cue.haptic_right)
        if cue.audio_text:
            self.audio.speak(cue.audio_text, urgent=cue.is_urgent)

    # ── Async run ──────────────────────────────────────────────────────────

    async def _sim_loop(self):
        interval = 1.0 / TICK_HZ
        log.info(f"[Sim] Running at {TICK_HZ} Hz. User walks {len(USER_PATH)} waypoints.")
        while True:
            self.tick()
            await asyncio.sleep(interval)

    async def _broadcast_loop(self):
        interval = cfg["map_stream"].get("update_interval_s", 0.2)
        while True:
            await self.map_stream.broadcast_grid(self.grid.to_dict())
            if self._path:
                await self.map_stream.broadcast_path(self._path)
            await asyncio.sleep(interval)

    async def run(self):
        self.audio.start()
        await self.map_stream.start()

        log.info("=" * 60)
        log.info("  BlindNav SIMULATION MODE")
        log.info("  WebSocket: ws://localhost:8765")
        log.info("  Open map viewer in browser:")
        log.info(r"  app_ui\map_viewer\index.html")
        log.info("=" * 60)

        # Auto-plan the initial path
        self._replan()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._sim_loop(),      name="sim_tick")
            tg.create_task(self._broadcast_loop(), name="broadcast")


def main():
    asyncio.run(Simulation().run())


if __name__ == "__main__":
    main()
