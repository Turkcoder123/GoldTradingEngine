"""Command line for the temporary live layer (`docs/live.md`).

`stream_live.py` streams SiftingIO ticks (gold and EUR/USD) and polls the
Dukascopy feed once a minute for the dollar index, aggregating everything into
in-memory 1-minute buffers and printing every bar that closes. Nothing is
written to the stored CSV history: the keeper stays the authority, the live
layer only fills the gap between two of its refreshes.
"""

from __future__ import annotations

import argparse
import json

from ...core import live_client, live_feed, live_params
from ...shared import config, version


def _series_argument(value: str) -> list:
    """'xauusd,eurusd' -> ['xauusd', 'eurusd'], rejecting unknown keys."""
    wanted = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in wanted
               if item not in live_params.DEFAULT_LIVE_SERIES]
    if not wanted or unknown:
        raise argparse.ArgumentTypeError(
            f"unknown live series {', '.join(unknown) or value!r}, expected "
            f"one of {', '.join(live_params.DEFAULT_LIVE_SERIES)}")
    return wanted


def _side_argument(value: str) -> str:
    """'b', 'BID' -> 'B'; anything else is a usage error."""
    try:
        return config.normalize_side(value)
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
        description="Streams SiftingIO ticks and polls the Dukascopy dollar "
                    "index into temporary in-memory 1-minute buffers.")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--series", type=_series_argument,
        default=list(live_params.DEFAULT_LIVE_SERIES),
        help="comma separated live series (default: %(default)s)")
    parser.add_argument(
        "--side", type=_side_argument, default=config.DEFAULT_SIDE,
        help="quote side used for the tick price (default: %(default)s)")
    parser.add_argument(
        "--buffer-minutes", type=int, default=live_params.BUFFER_MINUTES,
        help="live bars kept in memory per series (default: %(default)s)")
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


def format_bar(series_key: str, bar: dict) -> str:
    """One closed live bar as a text line; volume is printed when reported."""
    detail = (f"{bar['ticks']} ticks" if bar.get("ticks")
              else f"volume {bar['volume']:g}")
    return ("   %s  %-6s O %12.5f  H %12.5f  L %12.5f  C %12.5f  %s" % (
        bar["minute"], series_key, bar["open"], bar["high"], bar["low"],
        bar["close"], detail))


def format_summary(summary: dict) -> str:
    """Counters of one run plus the stored boundary of every series."""
    bars = summary.get("bars") or {}
    boundaries = summary.get("boundary") or {}
    counts = " ".join(f"{key}={count}" for key, count in bars.items()) or "-"
    bounds = " ".join(f"{key}={value or 'empty'}"
                      for key, value in boundaries.items()) or "-"
    return (" live buffer %s | %d ticks | %d ignored frames | %d errors | "
            "%d reconnects\n boundaries %s" % (
                counts, summary.get("accepted", 0), summary.get("ignored", 0),
                summary.get("errors", 0), summary.get("reconnects", 0), bounds))


def _emit(series_key: str, bar: dict, args) -> None:
    """Prints one closed bar as JSON or as a text line."""
    if args.quiet:
        return
    if args.json:
        print(json.dumps(dict(series=series_key, **bar), ensure_ascii=True),
              flush=True)
    else:
        print(format_bar(series_key, bar), flush=True)


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    try:
        session = live_feed.LiveSession(
            data_dir, args.series, args.side, args.buffer_minutes,
            on_bar=lambda series_key, bar: _emit(series_key, bar, args))
    except (live_client.LiveFeedError, ValueError) as exc:
        print(f" ! {exc}")
        return 1
    if not args.quiet:
        print(f" live layer {', '.join(args.series)} ({args.side}) -> "
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
