"""Tests for the live stream command line (no socket, no API key)."""

import json

import pytest

from src.core import live_client, live_params
from src.features.cli import live_app
from src.shared import config


def test_the_parser_defaults_match_the_registry():
    args = live_app.build_parser().parse_args([])
    assert args.series == config.DEFAULT_SERIES
    assert args.side == config.DEFAULT_SIDE
    assert args.buffer_minutes == live_params.BUFFER_MINUTES
    assert args.seconds is None
    assert args.json is False


def test_the_parser_rejects_an_unknown_side():
    with pytest.raises(SystemExit):
        live_app.build_parser().parse_args(["--side", "mid"])


def test_the_parser_rejects_an_unknown_series():
    with pytest.raises(SystemExit):
        live_app.build_parser().parse_args(["--series", "spx"])


def test_a_closed_bar_is_printed_with_its_ohlc():
    bar = {"minute": "2026-11-09 12:01:00", "open": 1.0, "high": 2.0,
           "low": 0.5, "close": 1.5, "ticks": 7, "volume": None}
    line = live_app.format_bar(bar)
    assert "2026-11-09 12:01:00" in line
    assert "1.500" in line and "7 ticks" in line


def test_the_summary_names_the_boundary_and_the_counters():
    line = live_app.format_summary(
        {"bars": 2, "accepted": 5, "ignored": 1, "reconnects": 0,
         "boundary": "2026-11-09 12:00:00"})
    assert "2 bars" in line and "5 ticks" in line
    assert "2026-11-09 12:00:00" in line


def test_an_empty_buffer_reads_empty(monkeypatch):
    line = live_app.format_summary(
        {"bars": 0, "accepted": 0, "ignored": 0, "reconnects": 0,
         "boundary": None})
    assert "empty" in line


def test_main_reports_a_missing_api_key(monkeypatch, capsys):
    monkeypatch.delenv(live_params.API_KEY_ENV, raising=False)
    monkeypatch.setattr(live_client.envfile, "read", lambda path: {})
    assert live_app.main([]) == 1
    assert "TWELVE_DATA_API_KEY" in capsys.readouterr().out


class _FakeSession:
    """Stands in for the session so no socket is opened."""

    def __init__(self, data_dir, series, side, minutes, on_bar=None, **kwargs):
        self.data_dir = data_dir
        self.series = series
        self.side = side
        self.minutes = minutes
        self.on_bar = on_bar
        self.stopped = False

    def run(self, max_seconds=None):
        self.on_bar({"minute": "2026-11-09 12:01:00", "open": 1.0,
                     "high": 2.0, "low": 0.5, "close": 1.5, "ticks": 3,
                     "volume": None})
        return {"bars": 1, "accepted": 3, "ignored": 0, "reconnects": 0,
                "boundary": "2026-11-09 12:00:00"}

    def stop(self):
        self.stopped = True


def test_main_streams_and_prints_one_json_object_per_bar(monkeypatch, capsys):
    monkeypatch.setattr(live_app.live_feed, "LiveSession", _FakeSession)
    assert live_app.main(["--json"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    bars = [json.loads(line) for line in lines if line.startswith("{")]
    assert bars and bars[0]["ticks"] == 3


def test_main_passes_the_requested_series_and_side(monkeypatch):
    seen = {}

    class Recorder(_FakeSession):
        def __init__(self, data_dir, series, side, minutes, on_bar=None,
                     **kwargs):
            seen.update(series=series, side=side, minutes=minutes)
            super().__init__(data_dir, series, side, minutes, on_bar)

    monkeypatch.setattr(live_app.live_feed, "LiveSession", Recorder)
    assert live_app.main(["--series", "dxy", "--side", "A",
                          "--buffer-minutes", "7", "--quiet"]) == 0
    assert seen == {"series": "dxy", "side": config.SIDE_ASK, "minutes": 7}


def test_main_is_quiet_when_asked(monkeypatch, capsys):
    monkeypatch.setattr(live_app.live_feed, "LiveSession", _FakeSession)
    assert live_app.main(["--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_an_interrupt_exits_with_the_shell_convention(monkeypatch, capsys):
    class Interrupted(_FakeSession):
        def run(self, max_seconds=None):
            raise KeyboardInterrupt

    monkeypatch.setattr(live_app.live_feed, "LiveSession", Interrupted)
    assert live_app.main([]) == 130
    assert "interrupted" in capsys.readouterr().out
