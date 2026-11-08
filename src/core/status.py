"""Offline freshness report built from the stored files (no network access)."""

from __future__ import annotations

import os

from ..shared import config, timeutil
from . import csvfile


def status_snapshot(data_dir: str, side: str = config.DEFAULT_SIDE,
                    prefix: str = config.PREFIX) -> dict:
    """Snapshot of the stored history; IO problems are reported."""
    snapshot = {
        "data_dir": data_dir,
        "side": side,
        "prefix": prefix,
        "files": 0,
        "size_mb": 0.0,
        "newest_file": None,
        "first_bar": None,
        "last_bar": None,
        "stale_minutes": 0,
        "gaps": 0,
        "missing_minutes": 0,
        "format": config.HEADER,
        "error": None,
    }
    try:
        paths = csvfile.month_files(data_dir, side, prefix)
        snapshot.update(_describe(paths, side))
    except OSError as exc:
        snapshot["error"] = str(exc)
    return snapshot


def _describe(paths, side: str) -> dict:
    """File count, size and bar range of the monthly files of one side."""
    if not paths:
        return {}
    total_bytes = 0
    for path in paths:
        total_bytes += os.path.getsize(path)
    last_ms = csvfile.newest_ms(paths)
    first_ms = csvfile.oldest_ms(paths)
    gaps = csvfile.gap_report(paths[-1])
    stale = 0
    if last_ms:
        stale = max(0, int(
            (timeutil.utc_now() - timeutil.epoch_to_minute(last_ms)
             ).total_seconds() // 60))
    return {
        "files": len(paths),
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "newest_file": os.path.basename(paths[-1]),
        "first_bar": timeutil.ts_to_text(first_ms) if first_ms else None,
        "last_bar": timeutil.ts_to_text(last_ms) if last_ms else None,
        "stale_minutes": stale,
        "gaps": gaps["gaps"],
        "missing_minutes": gaps["missing_minutes"],
        "side": side,
    }
