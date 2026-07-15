"""Bot health heartbeat + tiny HTTP endpoint for Docker HEALTHCHECK."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_state: dict[str, Any] = {
    "ok": True,
    "service": "hermes-bot",
    "mode": "paper",
    "ts": None,
    "ts_epoch": 0.0,
    "last_turn": None,
    "summary": "booting",
}
_lock = threading.Lock()
_server: Optional[HTTPServer] = None


def _log_dir() -> Path:
    p = Path(os.environ.get("HERMES_LOG_DIR", "logs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_heartbeat(**extra: Any) -> Path:
    """Persist heartbeat JSON for file-based healthchecks."""
    now = datetime.now(timezone.utc)
    with _lock:
        _state["ok"] = True
        _state["ts"] = now.isoformat()
        _state["ts_epoch"] = now.timestamp()
        _state["mode"] = "paper"
        _state.update({k: v for k, v in extra.items() if v is not None})
        payload = dict(_state)
    path = _log_dir() / "heartbeat.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def mark_unhealthy(reason: str) -> None:
    with _lock:
        _state["ok"] = False
        _state["summary"] = reason
        _state["ts"] = datetime.now(timezone.utc).isoformat()
        _state["ts_epoch"] = time.time()
    write_heartbeat()


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return  # quiet

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/health", "/healthz", "/"):
            self.send_response(404)
            self.end_headers()
            return
        with _lock:
            body = dict(_state)
        # Stale if no heartbeat within max age
        max_age = float(os.environ.get("HERMES_HEARTBEAT_MAX_AGE", "900"))
        age = time.time() - float(body.get("ts_epoch") or 0)
        healthy = bool(body.get("ok")) and age <= max_age
        code = 200 if healthy else 503
        payload = json.dumps({**body, "healthy": healthy, "age_s": round(age, 1)})
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))


def start_health_server(port: Optional[int] = None) -> None:
    """Background daemon HTTP health server (idempotent)."""
    global _server
    if _server is not None:
        return
    port = int(port or os.environ.get("HERMES_HEALTH_PORT", "8080"))
    write_heartbeat(summary="health_server_start")

    def _run() -> None:
        global _server
        try:
            httpd = HTTPServer(("0.0.0.0", port), _Handler)
            _server = httpd
            logger.info("health server listening on :%s", port)
            httpd.serve_forever()
        except OSError as exc:
            logger.warning("health server failed to bind :%s — %s", port, exc)

    t = threading.Thread(target=_run, name="hermes-health", daemon=True)
    t.start()
