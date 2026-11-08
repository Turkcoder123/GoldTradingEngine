"""Human readable output: English only, one line per event (LANG-2)."""

from __future__ import annotations

from ...core import refresh
from ...shared import timeutil


def say(message: str) -> None:
    """One timestamped line on stdout; raises OSError without a pipe."""
    print(f"{timeutil.utc_now():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def format_refresh(result: refresh.RefreshResult) -> str:
    """One-line summary of a run: what was added or why nothing was."""
    if not result.ok:
        return (f" ! refresh failed: {result.error or 'unknown error'}"
                f"  (segments={result.segments},"
                f" pending={result.pending_minutes:,} min)")
    parts = []
    if result.added:
        parts.append(
            f" +{result.added:,} bars  {result.start} -> {result.end}")
    else:
        parts.append(f" already up to date  (last bar {result.last_bar})")
    if result.closure_hours:
        parts.append(
            f"  {result.closure_hours:g}h without bars (market closure)")
    if result.late:
        parts.append(f"  {result.late:,} late bar(s) ignored")
    if result.done:
        parts.append("  done")
    else:
        parts.append(f"  still {result.pending_minutes:,} min behind"
                     " (run again or raise --segments)")
    if result.files:
        parts.append(f"  files: {', '.join(result.files)}")
    return "".join(parts)


def format_status(snapshot: dict) -> list:
    """The freshness report as a list of lines (easy to test)."""
    lines = [
        f" data dir    : {snapshot['data_dir']}",
        f" series      : {snapshot.get('series', '-')}"
        f"  ({snapshot.get('instrument', '-')})",
        f" offer side  : {snapshot['side']}",
        f" files       : {snapshot['files']} CSV  ({snapshot['size_mb']} MB)",
        f" newest file : {snapshot['newest_file']}",
        f" format      : {snapshot['format']}",
        f" first bar   : {snapshot['first_bar']} UTC",
        f" last bar    : {snapshot['last_bar']} UTC",
        f" stale       : {snapshot['stale_minutes']} min",
        f" gaps        : {snapshot['gaps']}"
        f" ({snapshot['missing_minutes']} minutes without bars,"
        " market closures included)",
    ]
    if snapshot.get("error"):
        lines.append(f" error       : {snapshot['error']}")
    return lines


def print_status(snapshot: dict) -> None:
    """Writes the freshness report to stdout."""
    for line in format_status(snapshot):
        print(line)
