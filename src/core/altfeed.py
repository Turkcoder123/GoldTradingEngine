"""Download helper shared by the alternative sources: one URL, one error type."""

from __future__ import annotations

import urllib.request

from ..shared import config


class AltError(RuntimeError):
    """Raised when an alternative source cannot be downloaded."""


def download(url: str, timeout: float = config.ALT_TIMEOUT_SECONDS) -> bytes:
    """Fetches one URL with the project user agent; OSError becomes AltError."""
    request = urllib.request.Request(
        url, headers={"User-Agent": config.REQUEST_HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except OSError as exc:
        raise AltError(f"cannot download {url}: {exc}") from exc
