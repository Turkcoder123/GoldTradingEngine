"""Tests for the argument parser (surface only, no side effects)."""

import pytest

from src.features.cli import parser
from src.shared import config, version


def test_defaults_match_the_documented_values():
    args = parser.build_parser().parse_args([])
    assert args.data_dir is None
    assert args.lock_dir is None
    assert args.offer_side == config.DEFAULT_SIDE
    assert args.segment_hours == config.DEFAULT_SEGMENT_HOURS
    assert args.segments == config.DEFAULT_SEGMENTS
    assert args.empty_allowance_hours == config.DEFAULT_EMPTY_ALLOWANCE_HOURS
    assert args.timeout == config.DEFAULT_TIMEOUT_SECONDS
    assert args.interval == config.DEFAULT_INTERVAL_MINUTES
    assert args.loop is False
    assert args.status is False
    assert args.quiet is False
    assert args.no_lock is False


def test_offer_side_is_normalised_to_upper_case():
    args = parser.build_parser().parse_args(["--offer-side", "a"])
    assert args.offer_side == config.SIDE_ASK


def test_unknown_offer_side_is_a_usage_error():
    with pytest.raises(SystemExit):
        parser.build_parser().parse_args(["--offer-side", "mid"])


def test_since_accepts_a_date():
    args = parser.build_parser().parse_args(["--since", "2020-01-01"])
    assert args.since.year == 2020


def test_since_rejects_a_bad_date():
    with pytest.raises(SystemExit):
        parser.build_parser().parse_args(["--since", "01/01/2020"])


def test_version_prints_the_version_file(capsys):
    with pytest.raises(SystemExit) as exit_info:
        parser.build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert version.read_version() in capsys.readouterr().out


def test_version_text_reports_an_unreadable_version_file(monkeypatch):
    def fail(path=None):
        raise version.VersionError("VERSION is gone")

    monkeypatch.setattr(version, "read_version", fail)
    assert "unknown version" in parser.version_text()
