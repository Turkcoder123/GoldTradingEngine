"""Tests for the report command line (named to keep module names unique)."""

from __future__ import annotations

from src.features.report import app

ROWS = [("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1)]


def test_the_report_is_written_into_the_data_directory(tmp_path):
    assert app.main(["--data-dir", str(tmp_path)]) == 0
    path = tmp_path / app.DEFAULT_NAME
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("GOLD MARKET DATA")
    assert text.endswith("\n")


def test_output_can_print_to_stdout(tmp_path, capsys):
    assert app.main(["--data-dir", str(tmp_path), "--output", "-"]) == 0
    assert "GOLD MARKET DATA" in capsys.readouterr().out


def test_output_can_be_another_file(tmp_path):
    target = tmp_path / "reports" / "inventory.txt"
    code = app.main(["--data-dir", str(tmp_path), "--output", str(target),
                     "--quiet"])
    assert code == 0
    assert target.exists()


def test_a_successful_run_reports_the_path(tmp_path, capsys):
    assert app.main(["--data-dir", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    assert "+ data report:" in printed
    assert app.DEFAULT_NAME in printed


def test_quiet_prints_nothing_on_success(tmp_path, capsys):
    assert app.main(["--data-dir", str(tmp_path), "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_a_write_failure_is_reported(tmp_path, capsys, monkeypatch):
    def explode(path, text):
        raise OSError("read-only")

    monkeypatch.setattr(app, "write_report", explode)
    assert app.main(["--data-dir", str(tmp_path)]) == 1
    assert "cannot write" in capsys.readouterr().err


def test_the_report_lists_the_stored_series(tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    assert app.main(["--data-dir", str(tmp_path), "--quiet"]) == 0
    text = (tmp_path / app.DEFAULT_NAME).read_text(encoding="utf-8")
    assert "xauusd" in text
    assert "XAU/USD" in text
    assert "2026-11-06 23:00:00" in text
    assert "11.5" in text


def test_the_output_path_defaults_to_the_data_directory(tmp_path):
    path = app.output_path(app.build_parser().parse_args([]), str(tmp_path))
    assert path.endswith(app.DEFAULT_NAME)
    assert path.startswith(str(tmp_path))
