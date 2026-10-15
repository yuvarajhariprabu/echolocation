"""
replanning_trigger.py — Detect When A* Replanning Is Needed

Replanning is triggered when:
  1. A new static obstacle appears on the current planned path
  2. A dynamic object with confidence above threshold occupies a path tile
  3. User has deviated more than MAX_DEVIATION tiles from the planned path
  4. Goal tile becomes unreachable (blocked)
"""

from typing import List, Tuple
from ..mapping.tile_grid import TileGrid
from ..fusion.event_schema import FusedObstacle

MAX_DEVIATION_TILES  = 3      # trigger replan if user is this far from path
DYNAMIC_REPLAN_CONF  = 0.6    # trigger replan if dynamic object this confident is on path


class ReplanningTrigger:

    def __init__(self):
        self._prev_path_tiles = set()

    def should_replan(
        self,
        fused: FusedObstacle,
        path: List[Tuple[int, int]],
        grid: TileGrid,
    ) -> bool:
        if not path:
            return False

        path_tiles = set(path)

        # 1. New static obstacle on path?
        for (tx, ty) in path_tiles:
            if grid._static[ty, tx] == 1:
                return True

        # 2. Dynamic object on path above threshold?
        for (tx, ty) in path_tiles:
            if grid._dynamic[ty, tx] >= DYNAMIC_REPLAN_CONF:
                return True

        # 3. User has deviated from path?
        ux, uy = grid.user.tile_x, grid.user.tile_y
        min_dist = min(abs(ux-tx) + abs(uy-ty) for tx, ty in path_tiles)
        if min_dist > MAX_DEVIATION_TILES:
            return True

        self._prev_path_tiles = path_tiles
        return False
