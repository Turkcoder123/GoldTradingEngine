"""Command line surface of the dashboard: arguments, pid guard, wiring.

The page and the JSON API are built in `server.py`; this module only decides
where to listen, refuses a second start on the same address (`pidfile.py`) and
stops cleanly. Keeping the two apart keeps both files under the `MOD-2` limit.
"""

from __future__ import annotations

import argparse
import signal
import sys
from http.server import ThreadingHTTPServer

from ...shared import config
from . import payload
from .dashboard import DEFAULT_TTL_SECONDS, Dashboard
from .pidfile import PidFile, pid_path
from .server import make_handler

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="serve_dashboard.py",
        description="Serves the stored price, COT and macro data as a local "
                    "web page (standard library only, read-only).")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help="address to listen on (default %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="port to listen on (default %(default)s)")
    parser.add_argument("--data-dir", default=None,
                        help="data directory (default: $XAUUSD_DATA_DIR or "
                             "<project>/xauusd_data)")
    parser.add_argument("--ttl", type=float, default=DEFAULT_TTL_SECONDS,
                        help="seconds a built response is reused "
                             "(default %(default)s)")
    parser.add_argument("--pid-file", default=None,
                        help="where the PID file lives (default: "
                             "<data dir>/dashboard-<port>.pid)")
    parser.add_argument("--no-pid", action="store_true",
                        help="skip the PID file and the single-instance check")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {payload.version_text()}")
    return parser


def _on_stop_signal(signum, frame) -> None:
    """Turns SIGTERM into the same path as Ctrl-C, so cleanup still runs."""
    del signum, frame
    raise KeyboardInterrupt


def install_stop_handler() -> bool:
    """Lets SIGTERM stop the server cleanly; False when that is not possible."""
    try:
        signal.signal(signal.SIGTERM, _on_stop_signal)
    except (ValueError, OSError):
        return False
    return True


def _report_holder(guard: PidFile) -> None:
    """Explains which run holds the address and what to do about it."""
    pid = guard.record.get("pid", "?")
    print(f" ! this dashboard is already running on {guard.url} "
          f"(pid {pid})", file=sys.stderr)
    print(f"   pid file: {guard.path}", file=sys.stderr)
    print("   stop it first, use another --port, or pass --no-pid",
          file=sys.stderr)


def take_pid(args, data_dir: str):
    """PID guard of this address: the guard, None for --no-pid, False if held."""
    if args.no_pid:
        return None
    guard = PidFile(pid_path(data_dir, args.port, args.pid_file),
                    args.host, args.port)
    if guard.acquire():
        if guard.reason:
            print(f" ! {guard.reason}; continuing without a pid file",
                  file=sys.stderr)
        return guard
    _report_holder(guard)
    return False


def _serve(args, data_dir: str) -> int:
    """Binds the address, prints the banner and serves until Ctrl-C."""
    try:
        server = ThreadingHTTPServer(
            (args.host, args.port), make_handler(Dashboard(data_dir, args.ttl)))
    except OSError as exc:
        print(f" ! cannot listen on {args.host}:{args.port}: {exc}",
              file=sys.stderr)
        return 1
    print(f" dashboard : http://{server.server_address[0]}:"
          f"{server.server_address[1]}/", flush=True)
    print(f" data dir  : {data_dir}", flush=True)
    print(f" version   : {payload.version_text()}", flush=True)
    print(" stop      : Ctrl-C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
        return INTERRUPTED
    finally:
        server.server_close()
    return 0


def main(argv=None) -> int:
    """Command line entry point: 0 after a clean stop, 130 when interrupted."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    guard = take_pid(args, data_dir)
    if guard is False:
        return 1
    install_stop_handler()
    try:
        return _serve(args, data_dir)
    except KeyboardInterrupt:
        print("stopped")
        return INTERRUPTED
    finally:
        if guard is not None:
            guard.release()
