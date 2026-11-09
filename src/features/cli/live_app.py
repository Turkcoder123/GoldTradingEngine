"""Command line for the temporary Twelve Data live layer (`docs/live.md`).

`stream_live.py` streams XAU/USD ticks into an in-memory 1-minute buffer and
prints every bar the stream closes. Nothing is written to the stored CSV
history: Dukascopy stays the authoritative source, the live layer only fills the
gap between two of its fifteen minute refreshes.
"""

from __future__ import annotations

import argparse
import json

from ...core import live_client, live_feed, live_params
from ...shared import config, version


def _side_argument(value: str) -> str:
    """'b', 'BID' -> 'B'; anything else is a usage error."""
    try:
        return config.normalize_side(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _series_argument(value: str) -> str:
    """A registered price series key, lower case."""
    try:
        return config.resolve_series(value).key
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _version_text() -> str:
    """--version output; warns when VERSION cannot be read."""
    try:
        return f"%(prog)s {version.read_version()}"
    except version.VersionError as exc:
        return f"%(prog)s unknown version ({exc})"


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="stream_live.py",
        description="Streams Twelve Data ticks into a temporary in-memory "
                    "1-minute buffer (never written to the CSV history).")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--series", type=_series_argument, default=config.DEFAULT_SERIES,
        help="price series whose stored range sets the boundary "
             "(default: %(default)s)")
    parser.add_argument(
        "--side", type=_side_argument, default=config.DEFAULT_SIDE,
        help="quote side used for the tick price (default: %(default)s)")
    parser.add_argument(
        "--buffer-minutes", type=int, default=live_params.BUFFER_MINUTES,
        help="live bars kept in memory (default: %(default)s)")
    parser.add_argument(
        "--seconds", type=float, default=None,
        help="stop after that many seconds (default: run until interrupted)")
    parser.add_argument("--json", action="store_true",
                        help="one JSON object per closed bar")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    parser.add_argument("--version", action="version",
                        version=_version_text())
    return parser


def format_bar(bar: dict) -> str:
    """One closed live bar as a text line; volume stays unavailable."""
    return ("   %s  O %10.3f  H %10.3f  L %10.3f  C %10.3f  %3d ticks" % (
        bar["minute"], bar["open"], bar["high"], bar["low"], bar["close"],
        bar["ticks"]))


def format_summary(summary: dict) -> str:
    """Counters of one run: ticks, frames, reconnects and the boundary."""
    return (" live buffer: %d bars | %d ticks | %d ignored frames | "
            "%d reconnects | boundary %s" % (
                summary.get("bars", 0), summary.get("accepted", 0),
                summary.get("ignored", 0), summary.get("reconnects", 0),
                summary.get("boundary") or "empty"))


def _emit(bar: dict, args) -> None:
    """Prints one closed bar as JSON or as a text line."""
    if args.quiet:
        return
    print(json.dumps(bar, ensure_ascii=True) if args.json else format_bar(bar),
          flush=True)


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    try:
        session = live_feed.LiveSession(
            data_dir, args.series, args.side, args.buffer_minutes,
            on_bar=lambda bar: _emit(bar, args))
    except (live_client.LiveFeedError, ValueError) as exc:
        print(f" ! {exc}")
        return 1
    if not args.quiet:
        print(f" live stream {live_params.SYMBOL} ({args.side}) -> "
              f"{data_dir}", flush=True)
    try:
        summary = session.run(args.seconds)
    except KeyboardInterrupt:
        session.stop()
        print(" ! interrupted", flush=True)
        return 130
    if not args.quiet:
        print(format_summary(summary), flush=True)
    return 0
