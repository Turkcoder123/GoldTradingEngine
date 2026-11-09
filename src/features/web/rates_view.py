"""Real interest rates payload: per country latest plus the world median line.

The panel shows the derived rates (yield minus inflation) next to the macro
series they come from, with the equal weighted median as the "global" figure.
"""

from __future__ import annotations

import datetime as dt

from ...core import rates

POINT_DAYS = 730


def _window(points: list, days: int = POINT_DAYS) -> list:
    """Points of the last `days` days, oldest first."""
    if not points:
        return []
    cutoff = (dt.date.fromisoformat(points[-1][0])
              - dt.timedelta(days=days)).isoformat()
    return [point for point in points if point[0] >= cutoff]


def payload(data_dir: str) -> dict:
    """Everything the real rates block shows."""
    body = rates.status(data_dir)
    countries = [{
        "code": code,
        "label": described["label"],
        "rows": described["rows"],
        "date": described["last_date"],
        "latest": described["latest"],
        "change_1y": described["change_1y"],
        "stale": described.get("stale", False),
    } for code, described in body["countries"].items() if described["rows"]]
    world = body["world"]
    return {
        "countries": countries,
        "world": {
            "median": world["median"],
            "date": world["date"],
            "count": world["count"],
            "min": world["min"],
            "max": world["max"],
            "points": _window(world["points"]),
        },
    }
