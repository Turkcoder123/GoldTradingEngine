"""Live overlay of the dashboard: the newest published buffer of each series.

The live process publishes `<data dir>/live/last.json` (`core/live_snapshot.py`);
this module turns it into the body of `GET /api/live`. The overlay is read-only
and cannot fail a page: a missing, stale or malformed document answers an empty
map with the reason, and the chart simply draws the stored bars only.
"""

from __future__ import annotations

from ...shared import timeutil
from ...core import live_snapshot

MAX_MINUTES = 240
STALE_SECONDS = 600
SOURCE = "siftingio+dukascopy"


def _age_seconds(written_at, now) -> int | None:
    """Age of the document in seconds; None when its stamp is unusable."""
    stamp = timeutil.text_to_ms(str(written_at or ""))
    if not stamp:
        return None
    moment = now or timeutil.utc_now()
    return max(0, int(moment.timestamp() - stamp / 1000))


def payload(data_dir: str, now=None) -> dict:
    """Published live bars per series plus the age of the document."""
    document = live_snapshot.read(live_snapshot.path(data_dir))
    published = document.get("series")
    series = {}
    for key, bars in (published.items() if isinstance(published, dict) else ()):
        if isinstance(bars, list) and bars:
            series[key] = bars[-MAX_MINUTES:]
    age = _age_seconds(document.get("written_at"), now)
    return {
        "series": series,
        "written_at": document.get("written_at"),
        "age_seconds": age,
        "stale": age is None or age > STALE_SECONDS,
        "source": SOURCE,
    }
