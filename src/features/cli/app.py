"""Entry point wiring: parse arguments, lock, run, report (no domain logic)."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict

from ...core import feed, lock, refresh, status
from ...shared import config
from . import parser, report


def _refresh_settings(args) -> refresh.RefreshSettings:
    """Translate parsed arguments into the core settings object."""
    series = config.resolve_series(args.series)
    return refresh.RefreshSettings(
        segment_hours=args.segment_hours,
        max_segments=args.segments,
        empty_allowance_hours=args.empty_allowance_hours,
        since=args.since,
        prefix=series.prefix,
        feed=feed.FeedSettings(
            side=args.offer_side, timeout=args.timeout,
            instrument=series.instrument),
    )


def _print_status(args, data_dir: str) -> int:
    """--status: freshness report, offline and read-only."""
    series = config.resolve_series(args.series)
    snapshot = status.status_snapshot(data_dir, args.offer_side,
                                      series.prefix)
    snapshot["series"] = series.key
    snapshot["instrument"] = series.instrument
    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    else:
        report.print_status(snapshot)
    return 0 if snapshot["error"] is None else 1


def _run_once(args, data_dir: str) -> int:
    """One catch-up run, then a single summary line (or JSON)."""
    result = refresh.refresh_once(data_dir, _refresh_settings(args))
    if args.json:
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    elif not args.quiet or not result.ok:
        print(report.format_refresh(result))
    return 0 if result.ok else 1


def _run_loop(args, data_dir: str) -> int:
    """Refreshes forever; Ctrl-C ends the loop without a traceback."""
    interval = max(float(args.interval), config.MIN_INTERVAL_MINUTES) * 60
    report.say(f"update_1m: every {args.interval:g} min -> {data_dir}")
    failures = 0
    while True:
        result = refresh.refresh_once(data_dir, _refresh_settings(args))
        if result.ok:
            if result.added:
                report.say(f"+{result.added:,} bars"
                           f" ({result.start} -> {result.end})")
            elif not args.quiet:
                report.say(f"up to date (last bar {result.last_bar})")
            if failures:
                report.say(f"feed recovered after {failures} failure(s)")
            failures = 0
        else:
            failures += 1
            report.say(f"refresh failed ({failures}x): {result.error}")
        time.sleep(interval)


def _take_lock(args, data_dir: str):
    """Returns an acquired lock, or None after explaining why not."""
    if args.no_lock:
        return None
    guard = lock.Lock(config.lock_path(data_dir, args.lock_dir))
    if not guard.acquire():
        print(f" ! another update_1m run holds the lock: {guard.reason};"
              " wait for it or use --no-lock", file=sys.stderr)
        return None
    if not guard.enforced:
        print(f" ! {guard.reason}; continuing without a lock", file=sys.stderr)
    return guard


def _dispatch(args, data_dir: str) -> int:
    """Routes one invocation: freshness report, single run or loop."""
    if args.status:
        return _print_status(args, data_dir)
    guard = _take_lock(args, data_dir)
    if guard is None and not args.no_lock:
        return 1
    try:
        if args.loop:
            return _run_loop(args, data_dir)
        return _run_once(args, data_dir)
    finally:
        if guard is not None:
            guard.release()


def main(argv=None) -> int:
    """Command line entry point: 0 on success, non-zero on a real failure."""
    args = parser.build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    try:
        return _dispatch(args, data_dir)
    except KeyboardInterrupt:
        print("stopped", file=sys.stderr)
        return 130
    except BrokenPipeError:
        print("output pipe closed, stopping", file=sys.stderr)
        return 2
