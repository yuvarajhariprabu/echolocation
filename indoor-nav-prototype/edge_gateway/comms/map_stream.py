"""
map_stream.py — WebSocket Map State Broadcaster

Pushes live grid state to the map viewer UI (app_ui/map_viewer/index.html)
over WebSocket. The map viewer subscribes and re-renders on each message.

Protocol:
  Server → Client: JSON {"type": "grid_update", "data": <TileGrid.to_dict()>}
  Server → Client: JSON {"type": "path_update", "data": [[tx,ty], ...]}
  Client → Server: JSON {"type": "set_goal", "tx": N, "ty": N}   (optional)

Usage (internal — started by main.py):
    stream = MapStream(port=8765)
    await stream.start()
    await stream.broadcast_grid(grid.to_dict())
"""

import asyncio
import json
import logging
from typing import Optional, Callable

log = logging.getLogger(__name__)

try:
    import websockets
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False
    log.warning("[MapStream] websockets not installed — map UI disabled. pip install websockets")


class MapStream:

    def __init__(self, host: str = "localhost", port: int = 8765,
                 on_goal_callback: Optional[Callable] = None):
        self._host     = host
        self._port     = port
        self._clients  = set()
        self._on_goal  = on_goal_callback
        self._server   = None

    async def start(self):
        if not _WS_AVAILABLE:
            log.warning("[MapStream] Skipping WebSocket server — websockets not installed")
            return
        self._server = await websockets.serve(
            self._handler, self._host, self._port
        )
        log.info(f"[MapStream] WebSocket server running on ws://{self._host}:{self._port}")
        print(f"[MapStream] Open app_ui/map_viewer/index.html — connecting to ws://{self._host}:{self._port}")

    async def _handler(self, ws, path=""):
        self._clients.add(ws)
        log.info(f"[MapStream] Map viewer connected ({len(self._clients)} total)")
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "set_goal" and self._on_goal:
                        self._on_goal(msg.get("tx", 0), msg.get("ty", 0))
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def broadcast_grid(self, grid_dict: dict):
        """Send full grid state to all connected map viewers."""
        await self._broadcast({"type": "grid_update", "data": grid_dict})

    async def broadcast_path(self, path: list):
        """Send current A* path to all connected map viewers."""
        await self._broadcast({"type": "path_update", "data": path})

    async def _broadcast(self, msg: dict):
        if not self._clients:
            return
        raw = json.dumps(msg)
        await asyncio.gather(
            *(ws.send(raw) for ws in list(self._clients)),
            return_exceptions=True
        )
