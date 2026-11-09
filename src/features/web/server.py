"""HTTP surface of the dashboard: static assets plus a few read-only JSON API.

Standard library only (OPEN-2): `http.server` serves the page and four endpoints
built from the stored files. Nothing here writes to the data directory, so the
dashboard can run next to the updaters. Only this module knows about HTTP; the
payloads come from `dashboard.py` and the view modules of this package.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from ...shared import timeutil
from . import fred_view, locale, page, payload
from .dashboard import Dashboard

DEFAULT_MONTHS = 3
MAX_MONTHS = 24
DEFAULT_FRED_YEARS = fred_view.DEFAULT_YEARS
MAX_FRED_YEARS = 20
MIN_YEAR = 1900
MAX_YEAR = 2100
JSON_TYPE = "application/json; charset=utf-8"


def _int_param(query: dict, name: str, default: int, minimum: int,
               maximum: int) -> int:
    """Integer query parameter, clamped to [minimum, maximum]."""
    raw = (query.get(name) or [""])[0]
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def make_handler(dashboard: Dashboard):
    """Handler class bound to one dashboard instance (one data dir per server)."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:                # noqa: N802 (http.server API)
            """Every route is a GET; the bodies are built on demand."""
            parsed = urlparse(self.path)
            try:
                self._dispatch(parsed.path, parse_qs(parsed.query))
            except (BrokenPipeError, ConnectionResetError):
                return          # the browser closed the tab mid-answer

        def _dispatch(self, path: str, query: dict) -> None:
            """Routes one request; unknown paths answer 404 without a traceback."""
            if path in ("/", "/index.html"):
                return self._send_body(
                    200, page.MIME_TYPES[".html"],
                    page.render_page(page.read_template()).encode("utf-8"))
            if path == "/favicon.ico":
                return self._send_body(204, "", b"")
            if path.startswith("/static/"):
                return self._send_static(path[len("/static/"):])
            if path == "/api/overview":
                return self._send_json(
                    payload.success("overview", dashboard.overview()))
            if path.startswith("/api/series/"):
                return self._send_series(path.rsplit("/", 1)[-1], query)
            if path.startswith("/api/smc/"):
                return self._send_smc(path.rsplit("/", 1)[-1], query)
            if path == "/api/cot":
                return self._send_cot(query)
            if path == "/api/macro":
                return self._send_macro(query)
            if path == "/api/live":
                return self._send_json(
                    payload.success("live", dashboard.live()))
            if path == "/api/refresh":
                dashboard.refresh()
                return self._send_json(
                    payload.success("refresh", {"refreshed": True}))
            self._send_json(
                payload.failure("unknown", locale.text("error.not_found")), 404)

        def _send_series(self, key: str, query: dict) -> None:
            """Daily bars of one series; an unknown key is a client error."""
            months = _int_param(query, "months", DEFAULT_MONTHS, 0, MAX_MONTHS)
            try:
                body = dashboard.series(key.lower(), months)
            except ValueError as exc:
                return self._send_json(
                    payload.failure(
                        "series",
                        f"{locale.text('error.bad_series')}: {exc}"), 400)
            self._send_json(payload.success("series", body))

        def _send_smc(self, key: str, query: dict) -> None:
            """Detected structures of one series; an unknown key is a 400."""
            months = _int_param(query, "months", DEFAULT_MONTHS, 0, MAX_MONTHS)
            try:
                body = dashboard.smc(key.lower(), months)
            except ValueError as exc:
                return self._send_json(
                    payload.failure(
                        "smc", f"{locale.text('error.bad_series')}: {exc}"), 400)
            self._send_json(payload.success("smc", body))

        def _send_cot(self, query: dict) -> None:
            """COT reports of one year (the newest stored year by default)."""
            year = _int_param(query, "year", 0, MIN_YEAR, MAX_YEAR) or None
            try:
                body = dashboard.cot(year)
            except (OSError, ValueError) as exc:
                return self._send_json(
                    payload.failure("cot",
                                    f"{locale.text('error.build')}: {exc}"), 500)
            self._send_json(payload.success("cot", body))

        def _send_macro(self, query: dict) -> None:
            """Macro series plus the chart window."""
            years = _int_param(query, "years", DEFAULT_FRED_YEARS, 0,
                               MAX_FRED_YEARS)
            self._send_json(payload.success("macro", dashboard.macro(years)))

        def _send_static(self, name: str) -> None:
            """One asset from the static folder; traversal is refused."""
            found = page.static_body(name)
            if found is None:
                return self._send_json(
                    payload.failure("static", locale.text("error.not_found")),
                    404)
            content_type, data = found
            self._send_body(200, content_type, data)

        def _send_json(self, body: dict, status: int = 200) -> None:
            """JSON answer, ASCII only so no charset surprise can break it."""
            self._send_body(status, JSON_TYPE,
                            json.dumps(body, ensure_ascii=True).encode("utf-8"))

        def _send_body(self, status: int, content_type: str, data: bytes) -> None:
            """One complete response with an exact length (HTTP/1.1)."""
            self.send_response(status)
            if status != 204:              # 204 carries no body and no length
                if content_type:
                    self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if data:
                self.wfile.write(data)

        def log_message(self, fmt: str, *args) -> None:
            """One timestamped line per request, like the CLI report."""
            print(f"{timeutil.utc_now():%Y-%m-%d %H:%M:%S} {fmt % args}",
                  flush=True)

    return Handler
