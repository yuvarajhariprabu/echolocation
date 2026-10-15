"""
decision_engine.py — Guidance Decision Engine

Converts the fused obstacle + current path into actionable guidance cues.

Design rules implemented:
  1. Fast-path classes → immediate haptic (no audio delay).
  2. is_caution=True → generic caution only, never specific class guidance.
  3. Low-confidence single source → caution.
  4. Specific guidance (e.g. "person ahead") only when both models agree
     and confidence is sufficient.
"""

import yaml
import math
from pathlib import Path
from typing import Optional, List, Tuple
from ..fusion.event_schema import FusedObstacle
from ..mapping.tile_grid import TileGrid

_CLASS_DEF_PATH = Path(__file__).parent.parent.parent / "aiml" / "shared" / "class_definitions.yaml"
with open(_CLASS_DEF_PATH) as f:
    _defs = yaml.safe_load(f)

_SENSOR_CLASSES = {c["index"]: c for c in _defs["sensor_classes"]}
_VISION_CLASSES = {c["index"]: c for c in _defs["vision_classes"]}


class GuidanceCue:
    """A single guidance instruction for this decision cycle."""
    __slots__ = ["haptic_front", "haptic_left", "haptic_right",
                 "haptic_intensity", "audio_text", "is_urgent"]

    def __init__(self):
        self.haptic_front     = 0      # 0 = off, 90 = warn, 255 = near
        self.haptic_left      = 0
        self.haptic_right     = 0
        self.haptic_intensity = 0      # 0–255
        self.audio_text       = ""
        self.is_urgent        = False


class DecisionEngine:

    NEAR_CM = 40
    WARN_CM = 90

    def decide(
        self,
        fused: FusedObstacle,
        path: List[Tuple[int,int]],
        grid: TileGrid,
    ) -> GuidanceCue:
        cue = GuidanceCue()

        dist = fused.distance_cm
        sensor_cls = _SENSOR_CLASSES.get(fused.sensor_class, {})

        # ── Haptic intensities from raw distances ───────────────────────────
        # Fast path: always fires, regardless of confidence or camera status
        cue.haptic_front = self._intensity(fused.distance_cm)
        # (Left/right would come from raw sensor events — simplified here)

        # ── Audio / semantic guidance ─────────────────────────────────────
        if fused.is_caution:
            # Generic caution — never assert specific class
            if dist > 0 and dist < self.WARN_CM:
                cue.audio_text = "Caution"
                cue.is_urgent  = dist < self.NEAR_CM

        else:
            # Confident, agreed-upon result
            sensor_name = sensor_cls.get("name", "unknown")

            if sensor_name == "dropoff_edge":
                cue.audio_text = "Drop-off ahead — stop"
                cue.is_urgent  = True
                cue.haptic_front = 255

            elif sensor_name == "approaching":
                cue.audio_text = "Something approaching"
                cue.is_urgent  = True

            elif sensor_name == "static_obstacle":
                direction = self._direction_word(fused.direction_deg)
                if fused.vision_class is not None:
                    vcls = _VISION_CLASSES.get(fused.vision_class, {})
                    vcls_name = vcls.get("name", "")
                    if vcls_name and vcls_name != "unknown_object":
                        cue.audio_text = f"{vcls_name.replace('_', ' ')} {direction}"
                    else:
                        cue.audio_text = f"Obstacle {direction}"
                else:
                    cue.audio_text = f"Obstacle {direction}"

            elif sensor_name == "moving_object":
                cue.audio_text = "Moving object detected"

            elif sensor_name in ("open_space", "user_motion"):
                cue.audio_text = ""  # no alert needed

        # Path-based turn guidance (next waypoint direction)
        if len(path) > 2:
            turn = self._path_turn(path, grid)
            if turn and not cue.is_urgent:
                if not cue.audio_text:
                    cue.audio_text = turn

        return cue

    @staticmethod
    def _intensity(dist_cm: float) -> int:
        if dist_cm <= 0: return 0
        if dist_cm < DecisionEngine.NEAR_CM: return 255
        if dist_cm < DecisionEngine.WARN_CM: return 90
        return 0

    @staticmethod
    def _direction_word(deg: float) -> str:
        if -30 < deg < 30: return "ahead"
        if deg <= -30:     return "to your left"
        return "to your right"

    @staticmethod
    def _path_turn(path: List[Tuple[int,int]], grid: TileGrid) -> str:
        """Suggest turn direction based on the next waypoint on the path."""
        if len(path) < 2: return ""
        ux, uy = path[0]
        nx, ny = path[1]
        dx = nx - ux
        dy = ny - uy
        heading = grid.user.heading_deg
        angle = math.degrees(math.atan2(dx, dy)) - heading
        angle = (angle + 180) % 360 - 180

        if abs(angle) < 20:  return ""
        if angle > 0:        return "Turn right"
        return "Turn left"
