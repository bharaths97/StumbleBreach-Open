"""Loopback-only, read-only HTTP API for the dashboard read model."""

from __future__ import annotations

import argparse
import ipaddress
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

from .read_model import build_read_model, read_route


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4400
_STATIC_FILES = {
    "/": ("app.html", "text/html; charset=utf-8"),
    "/app.html": ("app.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/theme.css": ("public/theme.css", "text/css; charset=utf-8"),
    "/data-table.js": ("public/data-table.js", "text/javascript; charset=utf-8"),
    "/sidebar-drawer.js": ("public/sidebar-drawer.js", "text/javascript; charset=utf-8"),
    "/route-prefix.js": ("public/route-prefix.js", "text/javascript; charset=utf-8"),
}


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _handler_factory(
    root: Path | str | None,
    fixture: Mapping[str, Any] | None,
) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "StumbleBreachDashboard/1"

        def _json(
            self,
            status: int,
            payload: Mapping[str, Any],
            headers: Mapping[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = unquote(urlsplit(self.path).path)
            if path not in _STATIC_FILES and not path.startswith("/api/"):
                self._json(404, {"error": "unknown dashboard route", "state": "unknown"})
                return
            if path in _STATIC_FILES:
                filename, content_type = _STATIC_FILES[path]
                try:
                    body = (Path(__file__).parent / filename).read_bytes()
                except OSError:
                    self._json(404, {"error": "unknown dashboard route", "state": "unknown"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                payload = read_route(build_read_model(root, fixture=fixture), path)
            except KeyError:
                self._json(404, {"error": "unknown dashboard route", "state": "unknown"})
                return
            self._json(200, payload)

        def _reject_write(self) -> None:
            self._json(
                405,
                {"error": "dashboard API is read-only", "state": "rejected"},
                {"Allow": "GET"},
            )

        do_POST = _reject_write
        do_PUT = _reject_write
        do_PATCH = _reject_write
        do_DELETE = _reject_write
        do_HEAD = _reject_write

        def log_message(self, *_args: Any) -> None:
            return

    return DashboardHandler


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    root: Path | str | None = None,
    fixture: Mapping[str, Any] | None = None,
) -> ThreadingHTTPServer:
    """Create a stopped loopback-only dashboard server."""
    if not _loopback(host):
        raise ValueError("dashboard server must bind to loopback")
    return ThreadingHTTPServer((host, port), _handler_factory(root, fixture))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    with create_server(args.host, args.port) as server:
        print(f"dashboard listening on http://{args.host}:{server.server_address[1]}")
        server.serve_forever()


if __name__ == "__main__":
    main()
