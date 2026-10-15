/**
 * ws_client.js — WebSocket Client for BlindNav Map Viewer
 *
 * Handles connection lifecycle, reconnection, and message routing.
 */

class BlindNavWS {
  constructor(url, callbacks = {}) {
    this._url       = url;
    this._callbacks = callbacks;
    this._ws        = null;
    this._reconnectMs = 2000;
    this._connect();
  }

  _connect() {
    try {
      this._ws = new WebSocket(this._url);
    } catch (e) {
      this._scheduleReconnect();
      return;
    }

    this._ws.addEventListener("open", () => {
      console.log("[WS] Connected to gateway");
      if (this._callbacks.onStatus) this._callbacks.onStatus(true);
    });

    this._ws.addEventListener("message", (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "grid_update" && this._callbacks.onGrid) {
          this._callbacks.onGrid(msg.data);
        } else if (msg.type === "path_update" && this._callbacks.onPath) {
          this._callbacks.onPath(msg.data);
        }
      } catch (err) {
        console.warn("[WS] Parse error:", err);
      }
    });

    this._ws.addEventListener("close", () => {
      console.warn("[WS] Disconnected");
      if (this._callbacks.onStatus) this._callbacks.onStatus(false);
      this._scheduleReconnect();
    });

    this._ws.addEventListener("error", () => {
      this._ws.close();
    });
  }

  _scheduleReconnect() {
    setTimeout(() => this._connect(), this._reconnectMs);
  }

  sendGoal(tx, ty) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ type: "set_goal", tx, ty }));
    }
  }
}
