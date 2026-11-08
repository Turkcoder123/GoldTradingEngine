"""Tests for the human readable output helpers."""

from src.core import refresh
from src.features.cli import report
from src.shared import config

SNAPSHOT = {
    "data_dir": "/data",
    "side": config.SIDE_BID,
    "files": 2,
    "size_mb": 0.17,
    "newest_file": "xauusd_1m_2026-11.csv",
    "first_bar": "2026-11-01 00:00:00",
    "last_bar": "2026-11-06 21:59:00",
    "stale_minutes": 12,
    "gaps": 0,
    "missing_minutes": 0,
    "format": config.HEADER,
    "error": None,
}


def test_format_refresh_reports_added_bars():
    result = refresh.RefreshResult(
        ok=True, added=5, start="a", end="b", done=True)
    text = report.format_refresh(result)
    assert "+5 bars" in text
    assert text.endswith("done")


def test_format_refresh_reports_the_stored_last_bar():
    result = refresh.RefreshResult(
        ok=True, done=True, last_bar="2026-11-06 21:59:00")
    assert "last bar 2026-11-06 21:59:00" in report.format_refresh(result)


def test_format_refresh_reports_a_failure_with_pending_minutes():
    result = refresh.RefreshResult(ok=False, error="boom", pending_minutes=90)
    text = report.format_refresh(result)
    assert "refresh failed: boom" in text
    assert "pending=90 min" in text
    assert "None" not in text


def test_format_refresh_reports_closures_late_bars_and_files():
    result = refresh.RefreshResult(
        ok=True, added=3, start="a", end="b", closure_hours=48.0, late=2,
        files=("xauusd_1m_2026-11.csv",))
    text = report.format_refresh(result)
    assert "48h without bars (market closure)" in text
    assert "2 late bar(s) ignored" in text
    assert "still" in text
    assert "files: xauusd_1m_2026-11.csv" in text


def test_format_status_lists_every_field():
    lines = report.format_status(SNAPSHOT)
    joined = "\n".join(lines)
    assert "/data" in joined
    assert "xauusd_1m_2026-11.csv" in joined
    assert "2026-11-06 21:59:00 UTC" in joined
    assert "gaps" in joined
    assert not any("error" in line for line in lines)


def test_format_status_appends_the_error_line():
    broken = dict(SNAPSHOT, error="permission denied")
    assert report.format_status(broken)[-1].strip().startswith("error")


def test_say_writes_a_timestamped_line(capsys):
    report.say("hello")
    out = capsys.readouterr().out
    assert out.endswith("hello\n")
    assert out[:19].count("-") == 2
