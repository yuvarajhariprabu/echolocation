"""
dynamic_object_tracker.py — Moving Object Tracker with Temporal Decay

Maintains a separate registry of tracked dynamic objects (humans, moving
obstacles) beyond the tile grid's built-in dynamic layer.

Each tracked object has:
  - Last seen tile (tx, ty)
  - Estimated velocity (tx_delta, ty_delta per second) from position history
  - Confidence (decays exponentially each tick)
  - Vision class (person / unknown_object / etc.)

When confidence drops below EVICTION_THRESHOLD the object is removed.
"""

import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


EVICTION_THRESHOLD = 0.05   # remove object when confidence falls below this
DECAY_RATE         = 0.4    # confidence multiplied by (1 - rate*dt) per second


@dataclass
class TrackedObject:
    obj_id:      int
    tx:          int
    ty:          int
    vision_class: int
    confidence:  float
    last_seen:   float = field(default_factory=time.monotonic)
    # Velocity estimate (tiles/second)
    vel_x: float = 0.0
    vel_y: float = 0.0
    # History of positions for velocity estimation
    history: List[Tuple[int,int,float]] = field(default_factory=list)


class DynamicObjectTracker:

    def __init__(self):
        self._objects: Dict[int, TrackedObject] = {}
        self._next_id = 0

    def update(self, tx: int, ty: int, vision_class: int, confidence: float) -> int:
        """
        Add or update a dynamic object at (tx, ty).
        Association is done by proximity: nearest existing object within 3 tiles.
        Returns the assigned object ID.
        """
        nearest_id = self._find_nearest(tx, ty, max_dist=3)
        now = time.monotonic()

        if nearest_id is not None:
            obj = self._objects[nearest_id]
            dt = now - obj.last_seen
            if dt > 0:
                obj.vel_x = (tx - obj.tx) / dt
                obj.vel_y = (ty - obj.ty) / dt
            obj.tx           = tx
            obj.ty           = ty
            obj.confidence   = min(confidence, 1.0)
            obj.last_seen    = now
            obj.vision_class = vision_class
            obj.history.append((tx, ty, now))
            obj.history = obj.history[-10:]  # keep last 10
            return nearest_id
        else:
            obj_id = self._next_id
            self._next_id += 1
            self._objects[obj_id] = TrackedObject(
                obj_id=obj_id, tx=tx, ty=ty,
                vision_class=vision_class, confidence=confidence,
                last_seen=now
            )
            return obj_id

    def decay_all(self):
        """Apply time-based decay and evict low-confidence objects."""
        now = time.monotonic()
        to_remove = []
        for obj_id, obj in self._objects.items():
            dt = now - obj.last_seen
            obj.confidence *= max(0.0, 1.0 - DECAY_RATE * dt)
            if obj.confidence < EVICTION_THRESHOLD:
                to_remove.append(obj_id)
        for obj_id in to_remove:
            del self._objects[obj_id]

    def get_all(self) -> List[TrackedObject]:
        return list(self._objects.values())

    def _find_nearest(self, tx: int, ty: int, max_dist: int) -> Optional[int]:
        best_id   = None
        best_dist = max_dist + 1
        for obj_id, obj in self._objects.items():
            d = abs(obj.tx - tx) + abs(obj.ty - ty)
            if d < best_dist:
                best_dist = d
                best_id   = obj_id
        return best_id
