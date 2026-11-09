"""Minimal `.env` reader: KEY=VALUE lines, the process environment wins.

Provider keys stay out of the repository (GIT-6), so a local `.env` supplies
them during development. A value that is already exported in the process
environment is never overridden: a shell export or a CI secret stays
authoritative. A missing file is a normal state, not an error.
"""

from __future__ import annotations

import os

_COMMENT = "#"
_EXPORT_PREFIX = "export "
_QUOTES = ("'", '"')


def _unquote(value: str) -> str:
    """Removes one matching pair of surrounding quotes, if there is one."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in _QUOTES:
        return value[1:-1]
    return value


def parse(text: str) -> dict:
    """KEY=VALUE pairs of one `.env` text; comments and blanks are skipped."""
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(_COMMENT) or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith(_EXPORT_PREFIX):
            key = key[len(_EXPORT_PREFIX):].strip()
        if key:
            values[key] = _unquote(value.strip())
    return values


def read(path: str) -> dict:
    """Pairs of one file; a missing or unreadable file answers an empty map."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return parse(handle.read())
    except OSError:
        return {}


def load(path: str) -> dict:
    """Applies a `.env` to `os.environ` without overriding what is set."""
    values = read(path)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values
