"""Builds the API bodies for one data directory, with both caches (MOD-1).

Kept apart from `server.py` so the HTTP surface stays small (MOD-2) and so the
payload building can be tested without a socket.
"""

from __future__ import annotations

from . import cache, cot_view, fred_view, overview, price_view, smc_view

DEFAULT_TTL_SECONDS = 120.0


class Dashboard:
    """The four read-only sections of the page, built from the stored files."""

    def __init__(self, data_dir: str, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.data_dir = data_dir
        self._responses = cache.TtlCache(ttl_seconds)
        self._files = cache.DailyCache()

    def overview(self) -> dict:
        """Coverage and latest quotes of every stored series."""
        return self._responses.get_or_build(
            "overview", lambda: overview.payload(self.data_dir))

    def series(self, key: str, months: int) -> dict:
        """Daily bars of one price series for the requested window."""
        return self._responses.get_or_build(
            ("series", key, months),
            lambda: price_view.payload(self._files.file_aggregate,
                                       self.data_dir, key, months))

    def cot(self, year) -> dict:
        """Stored COT reports of one year (None: the newest stored year)."""
        return self._responses.get_or_build(
            ("cot", year), lambda: cot_view.payload(self.data_dir, year))

    def smc(self, key: str, months: int) -> dict:
        """Detected SMC structures of one price series window."""
        return self._responses.get_or_build(
            ("smc", key, months),
            lambda: smc_view.payload(self._files.file_aggregate,
                                     self.data_dir, key, months))

    def macro(self, years: int) -> dict:
        """Macro series with the chart window of the requested length."""
        return self._responses.get_or_build(
            ("macro", years), lambda: fred_view.payload(self.data_dir, years))

    def refresh(self) -> None:
        """Drops both caches; the next request reads the files again."""
        self._responses.clear()
        self._files.clear()
