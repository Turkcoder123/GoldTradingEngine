"""Tests for the CLI wiring (no network, no real feed)."""

import json

from src.core import refresh
from src.features.cli import app


def test_status_json_returns_zero(tmp_path, capsys):
    code = app.main(["--status", "--json", "--data-dir", str(tmp_path)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"] == 0
    assert payload["error"] is None


def test_status_text_returns_zero(tmp_path, capsys):
    code = app.main(["--status", "--data-dir", str(tmp_path)])
    assert code == 0
    assert "data dir" in capsys.readouterr().out


def test_run_once_returns_zero_on_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        app.refresh, "refresh_once",
        lambda data_dir, settings: refresh.RefreshResult(ok=True, done=True))
    code = app.main(["--data-dir", str(tmp_path)])
    assert code == 0
    assert "up to date" in capsys.readouterr().out


def test_run_once_returns_one_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        app.refresh, "refresh_once",
        lambda data_dir, settings: refresh.RefreshResult(
            ok=False, error="boom"))
    code = app.main(["--data-dir", str(tmp_path), "--quiet"])
    assert code == 1
    assert "boom" in capsys.readouterr().out


def test_run_once_json_is_machine_readable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        app.refresh, "refresh_once",
        lambda data_dir, settings: refresh.RefreshResult(ok=True, added=7))
    code = app.main(["--data-dir", str(tmp_path), "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["added"] == 7


def test_main_refuses_a_held_lock(tmp_path, monkeypatch, capsys):
    class HeldLock:
        """Stand-in for a lock another process is holding."""

        path = "held.lock"
        reason = "another run holds it"
        enforced = True

        def acquire(self):
            return False

        def release(self):
            pass

    monkeypatch.setattr(app.lock, "Lock", lambda path: HeldLock())
    code = app.main(["--data-dir", str(tmp_path)])
    assert code == 1
    assert "another update_1m run holds the lock" in capsys.readouterr().err


def test_settings_are_built_from_the_arguments(tmp_path):
    args = app.parser.build_parser().parse_args(
        ["--data-dir", str(tmp_path), "--segment-hours", "6",
         "--segments", "3", "--empty-allowance-hours", "24",
         "--since", "2026-01-01", "--timeout", "5", "--offer-side", "a"])
    settings = app._refresh_settings(args)
    assert settings.segment_hours == 6
    assert settings.max_segments == 3
    assert settings.empty_allowance_hours == 24
    assert settings.since.year == 2026
    assert settings.feed.side == "A"
    assert settings.feed.timeout == 5.0
