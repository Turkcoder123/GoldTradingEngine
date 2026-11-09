"""Runtime snapshot of the live buffers, published for the dashboard.

The live layer keeps its bars in memory (`docs/live.md`), and a second process
cannot read another process's memory, so the session publishes the buffers as
one small JSON document under `<data dir>/live/last.json`. It is runtime state,
not market history: rewritten on every closed bar, written atomically so a
reader never sees half a document, and ignored by git with the rest of the data
directory (`GIT-6`, `FLOW-9`).
"""

from __future__ import annotations

import json
import os

from ..shared import config, timeutil

_SUBDIR = "live"
_NAME = "last.json"


def path(data_dir: str) -> str:
    """Where the snapshot of one data directory lives."""
    return os.path.join(data_dir, _SUBDIR, _NAME)


def _stamp(written_at) -> str:
    """The document stamp: now, a given datetime, or an already formatted text."""
    if written_at is None:
        return timeutil.utc_now().strftime(config.TIMESTAMP_FORMAT)
    if isinstance(written_at, str):
        return written_at
    return written_at.strftime(config.TIMESTAMP_FORMAT)


def write(target: str, series: dict, written_at=None) -> None:
    """Writes one document atomically (temporary file, then a rename)."""
    document = {"written_at": _stamp(written_at), "series": series}
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    temporary = f"{target}.tmp"
    with open(temporary, "w", encoding=config.ENCODING) as handle:
        json.dump(document, handle, ensure_ascii=True, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, target)


def read(target: str) -> dict:
    """The published document, or an empty map when nothing usable exists."""
    try:
        with open(target, "r", encoding=config.ENCODING) as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return {}
    return document if isinstance(document, dict) else {}
