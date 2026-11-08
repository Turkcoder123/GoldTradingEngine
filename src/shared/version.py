"""Project version read from the single source of truth VERSION (VER-3)."""

from __future__ import annotations

import re

from . import config

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")


class VersionError(RuntimeError):
    """Raised when VERSION is missing, unreadable or not a version number."""


def read_version(path: str | None = None) -> str:
    """Contents of the VERSION file, validated as a version (VER-1)."""
    source = path or config.VERSION_FILE
    try:
        with open(source, "r", encoding=config.ENCODING) as handle:
            text = handle.read().strip()
    except OSError as exc:
        raise VersionError(f"cannot read {source}: {exc}") from exc
    if not _SEMVER_PATTERN.match(text):
        raise VersionError(f"{source} does not hold a version: {text!r}")
    return text
