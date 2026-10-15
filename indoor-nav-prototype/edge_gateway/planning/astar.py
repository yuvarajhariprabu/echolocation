"""
astar.py — A* Pathfinding on the Tile Grid

Finds shortest passable path from user position to a goal tile.
Works on the combined static + dynamic occupancy layers.

The heuristic is octile distance (allows diagonal movement).
If no path is found (blocked grid), returns an empty list.
"""

import heapq
import math
from typing import List, Tuple, Optional
from ..mapping.tile_grid import TileGrid   # tile_grid lives in mapping/, not planning/


def astar(
    grid: TileGrid,
    goal_tx: int,
    goal_ty: int,
    allow_diagonal: bool = False,
    dynamic_threshold: float = 0.4,
) -> List[Tuple[int, int]]:
    """
    Find path from user's current tile to (goal_tx, goal_ty).

    Args:
        grid:               The TileGrid instance (reads user position + passability)
        goal_tx/ty:         Goal tile coordinates
        allow_diagonal:     Allow 8-directional movement (default: 4-directional)
        dynamic_threshold:  Dynamic occupancy level above which a tile is impassable

    Returns:
        List of (tx, ty) tile coordinates from user position to goal (inclusive).
        Empty list if no path found.
    """
    start = (grid.user.tile_x, grid.user.tile_y)
    goal  = (goal_tx, goal_ty)

    if start == goal:
        return [start]

    if not grid.is_passable(goal_tx, goal_ty, dynamic_threshold):
        return []

    # Directions: 4-way or 8-way
    if allow_diagonal:
        directions = [
            (0,1),(0,-1),(1,0),(-1,0),
            (1,1),(1,-1),(-1,1),(-1,-1)
        ]
    else:
        directions = [(0,1),(0,-1),(1,0),(-1,0)]

    def heuristic(a, b):
        dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
        if allow_diagonal:
            return max(dx, dy) + (math.sqrt(2)-1) * min(dx, dy)
        return dx + dy

    # Priority queue: (f_score, tie_breaker, node)
    open_set  = []
    counter   = 0
    heapq.heappush(open_set, (0.0, counter, start))

    came_from = {}
    g_score   = {start: 0.0}
    f_score   = {start: heuristic(start, goal)}

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        cx, cy = current
        for dx, dy in directions:
            nx, ny = cx+dx, cy+dy
            neighbor = (nx, ny)

            if not grid.is_passable(nx, ny, dynamic_threshold):
                continue

            move_cost = math.sqrt(2) if (dx != 0 and dy != 0) else 1.0
            tentative_g = g_score[current] + move_cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor]   = tentative_g
                f_score[neighbor]   = tentative_g + heuristic(neighbor, goal)
                counter += 1
                heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))

    return []  # no path found
