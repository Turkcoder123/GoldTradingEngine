"""Tests for the shared JSON envelope of the dashboard API."""

from __future__ import annotations

from src.features.web import payload


def test_success_wraps_the_body_with_the_version_and_the_build_time():
    body = payload.success("overview", {"series": []})
    assert body["ok"] is True
    assert body["section"] == "overview"
    assert body["data"] == {"series": []}
    assert body["version"] == payload.version_text()
    assert len(body["generated_at"]) == len("2026-11-08 12:00:00")


def test_failure_carries_the_reason():
    body = payload.failure("series", "boom")
    assert body["ok"] is False
    assert body["section"] == "series"
    assert body["error"] == "boom"


def test_version_text_reports_an_unreadable_version(monkeypatch):
    def explode(path=None):
        raise payload.version.VersionError("VERSION is gone")

    monkeypatch.setattr(payload.version, "read_version", explode)
    assert payload.version_text() == "unknown"
