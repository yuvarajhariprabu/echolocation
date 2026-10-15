"""
tile_grid.py — 3-Layer Occupancy Grid

Layers:
  0: STATIC  — permanent obstacles (walls, furniture). Set and forgotten.
  1: DYNAMIC — humans / moving objects. Each cell has a confidence that
               decays exponentially over time (cleared if user not seen recently).
  2: USER    — single tile marking user position + heading direction (degrees).

Grid origin (0,0) is the user's starting position.
Coordinate convention: +X = right, +Y = forward (away from user).
"""

import numpy as np
import time
from dataclasses import dataclass, field
from typing import Tuple, Optional


TILE_FREE     = 0
TILE_OCCUPIED = 1
TILE_UNKNOWN  = -1


@dataclass
class GridCell:
    static_occupied: bool  = False
    dynamic_conf: float    = 0.0    # [0,1] — decays over time
    dynamic_class: int     = -1     # vision class of dynamic occupant


@dataclass
class UserState:
    tile_x: int   = 0
    tile_y: int   = 0
    heading_deg: float = 0.0   # 0=north/forward, 90=right, -90=left


class TileGrid:
    """
    2D tile grid with 3 layers.
    All coordinates are in tile units; call world_to_tile() to convert from metres.
    """

    def __init__(self, width: int = 100, height: int = 100,
                 tile_size_cm: float = 20.0,
                 dynamic_decay_rate: float = 0.3):
        """
        Args:
            width/height:      grid dimensions in tiles (centred on origin)
            tile_size_cm:      physical size of one tile (cm) — from gateway_config.yaml
            dynamic_decay_rate: per-second decay of dynamic confidence
        """
        self.width       = width
        self.height      = height
        self.tile_size_cm = tile_size_cm
        self.decay_rate   = dynamic_decay_rate
        self.origin_x     = width  // 2
        self.origin_y     = height // 2

        self._static   = np.zeros((height, width), dtype=np.int8)    # 0=free, 1=occupied, -1=unknown
        self._dynamic  = np.zeros((height, width), dtype=np.float32) # confidence [0,1]
        self._dyn_cls  = np.full((height, width), -1, dtype=np.int8)
        self._last_decay = time.monotonic()

        self.user = UserState()

    # ── Coordinate conversion ─────────────────────────────────────────────

    def world_to_tile(self, x_m: float, y_m: float) -> Tuple[int, int]:
        """Convert world coordinates (metres) to tile indices."""
        tx = int(x_m * 100 / self.tile_size_cm) + self.origin_x
        ty = int(y_m * 100 / self.tile_size_cm) + self.origin_y
        return np.clip(tx, 0, self.width-1), np.clip(ty, 0, self.height-1)

    def tile_to_world(self, tx: int, ty: int) -> Tuple[float, float]:
        x_m = (tx - self.origin_x) * self.tile_size_cm / 100.0
        y_m = (ty - self.origin_y) * self.tile_size_cm / 100.0
        return x_m, y_m

    # ── Layer writes ──────────────────────────────────────────────────────

    def set_static(self, tx: int, ty: int, occupied: bool):
        if self._in_bounds(tx, ty):
            self._static[ty, tx] = TILE_OCCUPIED if occupied else TILE_FREE

    def set_dynamic(self, tx: int, ty: int, confidence: float, vision_class: int = -1):
        if self._in_bounds(tx, ty):
            self._dynamic[ty, tx]  = min(confidence, 1.0)
            self._dyn_cls[ty, tx]  = vision_class

    def set_user(self, tx: int, ty: int, heading_deg: float):
        self.user.tile_x    = np.clip(tx, 0, self.width-1)
        self.user.tile_y    = np.clip(ty, 0, self.height-1)
        self.user.heading_deg = heading_deg

    # ── Dynamic decay ─────────────────────────────────────────────────────

    def decay_dynamic(self):
        """Apply time-based exponential decay to dynamic layer. Call each loop tick."""
        now = time.monotonic()
        dt  = now - self._last_decay
        self._last_decay = now
        factor = max(0.0, 1.0 - self.decay_rate * dt)
        self._dynamic *= factor
        # Clear cells that have decayed below threshold
        self._dyn_cls[self._dynamic < 0.05] = -1
        self._dynamic[self._dynamic < 0.05] = 0.0

    # ── Combined occupancy (for A*) ────────────────────────────────────────

    def is_passable(self, tx: int, ty: int, dynamic_threshold: float = 0.4) -> bool:
        if not self._in_bounds(tx, ty):
            return False
        if self._static[ty, tx] == TILE_OCCUPIED:
            return False
        if self._dynamic[ty, tx] >= dynamic_threshold:
            return False
        return True

    # ── Serialization for WebSocket map stream ─────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-serializable snapshot of the full grid state."""
        return {
            "width":  self.width,
            "height": self.height,
            "static":  self._static.tolist(),
            "dynamic": self._dynamic.round(2).tolist(),
            "dyn_cls": self._dyn_cls.tolist(),
            "user": {
                "tx":          self.user.tile_x,
                "ty":          self.user.tile_y,
                "heading_deg": self.user.heading_deg,
            },
            "tile_size_cm": self.tile_size_cm,
        }

    def _in_bounds(self, tx: int, ty: int) -> bool:
        return 0 <= tx < self.width and 0 <= ty < self.height
