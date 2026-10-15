"""
grid_updater.py — Apply Fused Obstacle Events onto the Tile Grid

Converts a FusedObstacle (distance + direction + class) into a tile
coordinate and marks it on the appropriate grid layer.

Static obstacles → static layer (permanent)
Moving objects   → dynamic layer (with confidence, decays over time)
"""

import math
from .tile_grid import TileGrid
from ..fusion.event_schema import FusedObstacle

# Sensor class indices (must match class_definitions.yaml)
MOVING_CLASSES  = {1, 4, 5, 6}   # moving_object, approaching, receding, crossing
DROPOFF_CLASS   = 3
OPEN_SPACE_CLASS = 2
USER_MOTION_CLASS = 7


class GridUpdater:

    def __init__(self, grid: TileGrid):
        self.grid = grid

    def update(self, fused: FusedObstacle):
        """Apply a fused obstacle event to the tile grid."""
        if fused.distance_cm <= 0:
            return   # no valid distance → nothing to plot

        if fused.fused_class in (OPEN_SPACE_CLASS, USER_MOTION_CLASS):
            return   # open space / user motion → don't mark obstacle

        # Convert polar (distance, direction) to tile offset from user
        heading   = self.grid.user.heading_deg
        abs_angle = math.radians(heading + fused.direction_deg)
        dist_m    = fused.distance_cm / 100.0

        dx_m = dist_m * math.sin(abs_angle)
        dy_m = dist_m * math.cos(abs_angle)

        obs_x_m = (self.grid.user.tile_x - self.grid.origin_x) * self.grid.tile_size_cm / 100.0 + dx_m
        obs_y_m = (self.grid.user.tile_y - self.grid.origin_y) * self.grid.tile_size_cm / 100.0 + dy_m

        tx, ty = self.grid.world_to_tile(obs_x_m, obs_y_m)

        if fused.fused_class in MOVING_CLASSES:
            # Dynamic layer — will decay over time
            self.grid.set_dynamic(tx, ty,
                                  confidence=fused.fused_confidence,
                                  vision_class=fused.vision_class if fused.vision_class is not None else -1)
        else:
            # Static layer — permanent
            self.grid.set_static(tx, ty, occupied=True)
