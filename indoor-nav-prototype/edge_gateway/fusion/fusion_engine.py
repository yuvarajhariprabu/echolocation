"""
fusion_engine.py — Sensor + Vision Fusion with Confidence Gating

Design rules implemented here:
  1. If sensor_confidence < threshold OR vision_confidence < threshold
     → is_caution = True, fused_class = unknown
  2. If both models fire but their classes conflict (and neither is a
     high-priority fast-path class) → is_caution = True
  3. Fast-path classes (drop-off, approaching) always assert regardless of
     camera confidence — camera enriches, never gates the safety response.
  4. Class label consistency: all class indices reference class_definitions.yaml
     (loaded here, not hardcoded).
"""

import yaml
import time
from pathlib import Path
from typing import Optional
from .event_schema import SensorEvent, VisionEvent, FusedObstacle

# Load class definitions
_CLASS_DEF_PATH = Path(__file__).parent.parent.parent / "aiml" / "shared" / "class_definitions.yaml"
with open(_CLASS_DEF_PATH) as f:
    _defs = yaml.safe_load(f)

CONFIDENCE_THRESHOLD = _defs["fusion"]["confidence_threshold"]  # 0.65
FAST_PATH_CLASSES    = set(_defs["fusion"]["fast_path_classes"])  # names

# Map sensor class names to indices for fast-path lookup
_SENSOR_CLASSES = {c["name"]: c["index"] for c in _defs["sensor_classes"]}
FAST_PATH_INDICES = {_SENSOR_CLASSES[n] for n in FAST_PATH_CLASSES if n in _SENSOR_CLASSES}
UNKNOWN_SENSOR_IDX = _SENSOR_CLASSES.get("unknown", 8)


class FusionEngine:
    """
    Stateless fusion: call fuse() each time a sensor or vision event arrives.
    Stores the latest of each event type; pairs them when both are fresh.
    """

    def __init__(self, max_vision_age_s: float = 2.0):
        self._last_sensor: Optional[SensorEvent] = None
        self._last_vision: Optional[VisionEvent] = None
        self._sensor_ts = 0.0
        self._vision_ts = 0.0
        self.max_vision_age_s = max_vision_age_s  # discard stale vision events

    def on_sensor_event(self, ev: SensorEvent) -> FusedObstacle:
        """Called when a new sensor event arrives. Always produces a fused result."""
        self._last_sensor = ev
        self._sensor_ts   = time.monotonic()
        return self._fuse()

    def on_vision_event(self, ev: VisionEvent) -> Optional[FusedObstacle]:
        """Called when a vision event arrives. Returns updated fusion if sensor is also fresh."""
        self._last_vision = ev
        self._vision_ts   = time.monotonic()
        if self._last_sensor is not None:
            return self._fuse()
        return None

    def _fuse(self) -> FusedObstacle:
        s = self._last_sensor

        # Determine closest direction and distance
        dists = {
            "front": s.front_cm if s.front_cm > 0 else float("inf"),
            "left":  s.left_cm  if s.left_cm  > 0 else float("inf"),
            "right": s.right_cm if s.right_cm > 0 else float("inf"),
        }
        closest_dir = min(dists, key=dists.get)
        closest_cm  = dists[closest_dir]
        direction_deg = {"front": 0.0, "left": -60.0, "right": 60.0}[closest_dir]

        # Vision availability
        now = time.monotonic()
        vision_fresh = (
            self._last_vision is not None and
            (now - self._vision_ts) < self.max_vision_age_s
        )
        v = self._last_vision if vision_fresh else None

        # ── Confidence gating ─────────────────────────────────────────────
        sensor_ok  = s.confidence >= CONFIDENCE_THRESHOLD
        vision_ok  = v is not None and v.confidence >= CONFIDENCE_THRESHOLD
        is_fast    = s.class_index in FAST_PATH_INDICES

        # Fast-path classes always assert (design rule #1)
        if is_fast:
            fused_class = s.class_index
            fused_conf  = s.confidence
            is_caution  = False
        elif not sensor_ok:
            # Sensor itself is uncertain → generic caution
            fused_class = UNKNOWN_SENSOR_IDX
            fused_conf  = s.confidence
            is_caution  = True
        elif v is None or not vision_ok:
            # No valid vision → trust sensor alone if confident
            fused_class = s.class_index
            fused_conf  = s.confidence
            is_caution  = False
        else:
            # Both models fired with sufficient confidence
            # Agreement check: both agree on obstacle presence (not open_space vs obstacle)
            sensor_is_obstacle = s.class_index not in (2, 7)  # not open_space or user_motion
            vision_is_obstacle = v.class_index < 6            # not unknown_object
            if sensor_is_obstacle != vision_is_obstacle:
                # Disagree on whether there's an obstacle → caution
                fused_class = UNKNOWN_SENSOR_IDX
                fused_conf  = min(s.confidence, v.confidence)
                is_caution  = True
            else:
                # Both agree → blend confidence, take sensor class (higher temporal resolution)
                fused_class = s.class_index
                fused_conf  = (s.confidence + v.confidence) / 2
                is_caution  = False

        return FusedObstacle(
            ts                = s.ts,
            direction_deg     = direction_deg,
            distance_cm       = closest_cm if closest_cm < float("inf") else -1,
            sensor_class      = s.class_index,
            sensor_confidence = s.confidence,
            vision_class      = v.class_index  if v else None,
            vision_confidence = v.confidence   if v else 0.0,
            vision_grid_x     = v.grid_x       if v else 0,
            vision_grid_y     = v.grid_y       if v else 0,
            fused_class       = fused_class,
            fused_confidence  = fused_conf,
            is_caution        = is_caution,
            is_moving         = s.class_index in (1, 4, 5, 6),
            user_stationary   = s.stationary,
        )
