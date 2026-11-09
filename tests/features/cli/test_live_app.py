"""Tests for the live stream command line (no socket, no API key)."""

import json

import pytest

from src.core import live_client, live_params
from src.features.cli import live_app
from src.shared import config


def test_the_parser_defaults_cover_every_live_series():
    args = live_app.build_parser().parse_args([])
    assert args.series == list(live_params.DEFAULT_LIVE_SERIES)
    assert args.side == config.DEFAULT_SIDE
    assert args.buffer_minutes == live_params.BUFFER_MINUTES
    assert args.seconds is None


def test_the_parser_accepts_a_subset():
    args = live_app.build_parser().parse_args(["--series", "dxy,xauusd"])
    assert args.series == ["dxy", "xauusd"]


def test_the_parser_rejects_an_unknown_series():
    with pytest.raises(SystemExit):
        live_app.build_parser().parse_args(["--series", "xagusd"])


def test_the_parser_rejects_an_unknown_side():
    with pytest.raises(SystemExit):
        live_app.build_parser().parse_args(["--side", "mid"])


def test_a_tick_bar_is_printed_with_its_series_and_tick_count():
    bar = {"minute": "2026-11-09 12:01:00", "open": 1.0, "high": 2.0,
           "low": 0.5, "close": 1.5, "ticks": 7, "volume": None}
    line = live_app.format_bar("xauusd", bar)
    assert "xauusd" in line and "1.50000" in line and "7 ticks" in line


def test_a_polled_bar_prints_its_volume():
    bar = {"minute": "2026-11-09 12:01:00", "open": 101.0, "high": 101.5,
           "low": 100.5, "close": 101.2, "ticks": 0, "volume": 0.25}
    assert "volume 0.25" in live_app.format_bar("dxy", bar)


def test_the_summary_names_every_series_and_boundary():
    line = live_app.format_summary(
        {"accepted": 5, "ignored": 1, "errors": 0, "reconnects": 0,
         "bars": {"xauusd": 2, "dxy": 1},
         "boundary": {"xauusd": "2026-11-09 12:00:00", "dxy": None}})
    assert "xauusd=2" in line and "dxy=1" in line
    assert "2026-11-09 12:00:00" in line and "dxy=empty" in line


def test_main_reports_a_missing_api_key_for_a_streamed_series(monkeypatch,
                                                              capsys):
    monkeypatch.delenv(live_params.API_KEY_ENV, raising=False)
    monkeypatch.setattr(live_client.envfile, "read", lambda path: {})
    assert live_app.main(["--series", "xauusd"]) == 1
    assert "SIFTING_API_KEY" in capsys.readouterr().out


class _FakeSession:
    """Stands in for the session so no socket is opened."""

    def __init__(self, data_dir, series, side, minutes, on_bar=None, **kwargs):
        self.series = series
        self.on_bar = on_bar
        self.stopped = False

    def run(self, max_seconds=None):
        self.on_bar("xauusd", {"minute": "2026-11-09 12:01:00", "open": 1.0,
                               "high": 2.0, "low": 0.5, "close": 1.5,
                               "ticks": 3, "volume": None})
        return {"accepted": 3, "ignored": 0, "errors": 0, "reconnects": 0,
                "bars": {"xauusd": 1},
                "boundary": {"xauusd": "2026-11-09 12:00:00"}}

    def stop(self):
        self.stopped = True


def test_main_streams_and_prints_one_json_object_per_bar(monkeypatch, capsys):
    monkeypatch.setattr(live_app.live_feed, "LiveSession", _FakeSession)
    assert live_app.main(["--json"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    bars = [json.loads(line) for line in lines if line.startswith("{")]
    assert bars and bars[0]["series"] == "xauusd" and bars[0]["ticks"] == 3


def test_main_passes_the_requested_series_side_and_buffer(monkeypatch):
    seen = {}

    class Recorder(_FakeSession):
        def __init__(self, data_dir, series, side, minutes, on_bar=None,
                     **kwargs):
            seen.update(series=series, side=side, minutes=minutes)
            super().__init__(data_dir, series, side, minutes, on_bar)

    monkeypatch.setattr(live_app.live_feed, "LiveSession", Recorder)
    assert live_app.main(["--series", "dxy", "--side", "A",
                          "--buffer-minutes", "7", "--quiet"]) == 0
    assert seen == {"series": ["dxy"], "side": config.SIDE_ASK, "minutes": 7}


def test_main_is_quiet_when_asked(monkeypatch, capsys):
    monkeypatch.setattr(live_app.live_feed, "LiveSession", _FakeSession)
    assert live_app.main(["--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_the_snapshot_flags_are_forwarded(monkeypatch):
    seen = {}

    class Recorder(_FakeSession):
        def __init__(self, data_dir, series, side, minutes, on_bar=None,
                     **kwargs):
            seen.update(kwargs)
            super().__init__(data_dir, series, side, minutes, on_bar)

    monkeypatch.setattr(live_app.live_feed, "LiveSession", Recorder)
    assert live_app.main(["--series", "dxy", "--quiet", "--no-snapshot"]) == 0
    assert seen == {"publish": False, "snapshot_path": None}
    seen.clear()
    assert live_app.main(["--series", "dxy", "--quiet",
                          "--snapshot", "/tmp/x.json"]) == 0
    assert seen == {"publish": True, "snapshot_path": "/tmp/x.json"}


def test_an_interrupt_exits_with_the_shell_convention(monkeypatch, capsys):
    class Interrupted(_FakeSession):
        def run(self, max_seconds=None):
            raise KeyboardInterrupt

    monkeypatch.setattr(live_app.live_feed, "LiveSession", Interrupted)
    assert live_app.main([]) == 130
    assert "interrupted" in capsys.readouterr().out
