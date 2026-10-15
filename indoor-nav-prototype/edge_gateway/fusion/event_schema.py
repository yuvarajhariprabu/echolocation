"""
event_schema.py — Pydantic Data Classes for BLE Event Payloads

All events flowing through the gateway are typed and validated here.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SensorEvent:
    """Parsed event from the ESP32-S3 sensor node."""
    ts: int                  # device millis timestamp
    class_index: int         # sensor class 0–8
    confidence: float        # softmax confidence [0,1]
    front_cm: float          # ultrasonic front distance (cm), -1 = out of range
    left_cm: float           # ultrasonic left distance (cm)
    right_cm: float          # ultrasonic right distance (cm)
    floor_mm: int            # VL53L0X floor reading (mm), 0 = invalid
    yaw_rate_dps: float      # IMU yaw rate (deg/s)
    stationary: bool         # True if ZUPT detected

    @property
    def is_fast_path(self) -> bool:
        """True if this event should trigger immediate haptic (no wait for camera)."""
        return self.class_index in (0, 3, 4)  # static_obstacle, dropoff_edge, approaching


@dataclass
class VisionEvent:
    """Parsed event from the ESP32-CAM vision node."""
    ts: int
    class_index: int         # vision class 0–6
    confidence: float        # FOMO peak activation [0,1]
    grid_x: int              # FOMO output grid column
    grid_y: int              # FOMO output grid row


@dataclass
class FusedObstacle:
    """
    Fused result combining sensor + vision events + IMU heading.
    This is the object that drives mapping, planning, and guidance.
    """
    ts: int
    # Geometry
    direction_deg: float         # obstacle direction relative to user heading (0=front)
    distance_cm: float           # estimated distance to obstacle

    # Sensor model output
    sensor_class: int
    sensor_confidence: float

    # Vision model output (None if camera did not fire or returned unknown)
    vision_class: Optional[int]  = None
    vision_confidence: float     = 0.0
    vision_grid_x: int           = 0
    vision_grid_y: int           = 0

    # Fusion decision
    fused_class: int             = 8     # default: unknown
    fused_confidence: float      = 0.0
    is_caution: bool             = True  # True = use generic caution, not specific guidance

    # Dynamic tracking
    is_moving: bool              = False
    user_stationary: bool        = False
