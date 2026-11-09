"""Common JSON envelope for every dashboard endpoint (one shape for all)."""

from __future__ import annotations

from ...shared import config, timeutil, version


def version_text() -> str:
    """The project version, or a readable placeholder when VERSION is broken."""
    try:
        return version.read_version()
    except version.VersionError:
        return "unknown"


def success(section: str, body: dict) -> dict:
    """Wraps a section body: ok flag, version and the build time (UTC)."""
    return {
        "ok": True,
        "section": section,
        "version": version_text(),
        "generated_at": timeutil.utc_now().strftime(config.TIMESTAMP_FORMAT),
        "data": body,
    }


def failure(section: str, error: str) -> dict:
    """Wraps an error so the page shows one message instead of breaking."""
    return {"ok": False, "section": section, "error": error}
