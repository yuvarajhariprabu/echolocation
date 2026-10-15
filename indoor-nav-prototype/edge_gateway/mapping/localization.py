"""
localization.py — IMU Dead-Reckoning Position + Heading Update

Updates the user's tile position and heading on the TileGrid from
incoming sensor events (yaw_rate_dps, IMU dead-reckoning position).

Dead-reckoning is drift-prone. The position is only used for:
  - Placing the user marker on the map
  - A* start-tile lookup
It is NOT safety-critical; the safety response comes from raw sensor distances.
"""

import math
import time
from .tile_grid import TileGrid
from ..fusion.event_schema import SensorEvent


class Localization:

    def __init__(self, grid: TileGrid):
        self.grid = grid
        self._heading_deg = 0.0       # accumulated heading from yaw rate
        self._pos_x_m    = 0.0
        self._pos_y_m    = 0.0
        self._last_ts    = None       # last event timestamp (ms)

    def update(self, ev: SensorEvent):
        """
        Integrate yaw rate to update heading.
        Use ev position fields if the firmware has done dead-reckoning,
        otherwise integrate from yaw_rate_dps.
        """
        if self._last_ts is None:
            self._last_ts = ev.ts
            return

        dt_s = (ev.ts - self._last_ts) / 1000.0
        if dt_s <= 0:
            return
        self._last_ts = ev.ts

        # Integrate heading from yaw rate
        self._heading_deg = (self._heading_deg + ev.yaw_rate_dps * dt_s) % 360.0

        # Advance position using sensor stationary flag
        # When user is moving (not stationary), project position forward
        if not ev.stationary:
            # Estimate forward speed from closest obstacle distance delta (very crude)
            # For prototype, this provides approximate tile movement
            heading_rad = math.radians(self._heading_deg)
            # Assume ~0.5 m/s walking speed when moving; updates at 20Hz
            step_m = 0.5 * dt_s
            self._pos_x_m += step_m * math.sin(heading_rad)
            self._pos_y_m += step_m * math.cos(heading_rad)

        # Update grid user tile
        tx, ty = self.grid.world_to_tile(self._pos_x_m, self._pos_y_m)
        self.grid.set_user(tx, ty, self._heading_deg)

    def reset(self):
        """Call when user is at a known position (landmark reset)."""
        self._pos_x_m    = 0.0
        self._pos_y_m    = 0.0
        self._heading_deg = 0.0
        tx, ty = self.grid.world_to_tile(0.0, 0.0)
        self.grid.set_user(tx, ty, 0.0)
