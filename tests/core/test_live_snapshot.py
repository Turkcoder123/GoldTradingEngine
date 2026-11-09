"""Tests for the published live snapshot (runtime state, not history)."""

import os

from src.core import live_snapshot


def test_the_path_lives_next_to_the_data(tmp_path):
    assert live_snapshot.path(str(tmp_path)).endswith("live/last.json")


def test_write_then_read_round_trips_the_bars(tmp_path):
    target = live_snapshot.path(str(tmp_path))
    bars = {"xauusd": [{"minute": "2026-11-09 08:12:00", "close": 4090.32}]}
    live_snapshot.write(target, bars)
    document = live_snapshot.read(target)
    assert document["series"] == bars
    assert document["written_at"]


def test_the_write_leaves_no_temporary_file(tmp_path):
    target = live_snapshot.path(str(tmp_path))
    live_snapshot.write(target, {"dxy": []})
    leftovers = [name for name in os.listdir(os.path.dirname(target))
                 if name.endswith(".tmp")]
    assert leftovers == []


def test_reading_a_missing_document_answers_an_empty_map(tmp_path):
    assert live_snapshot.read(live_snapshot.path(str(tmp_path))) == {}


def test_reading_a_broken_document_answers_an_empty_map(tmp_path):
    target = tmp_path / "live" / "last.json"
    target.parent.mkdir(parents=True)
    target.write_text("{not json", encoding="utf-8")
    assert live_snapshot.read(str(target)) == {}
