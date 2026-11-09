"""The HTML shell and the static assets served by the dashboard.

The page carries no text of its own: `index.html` holds placeholders that are
filled from `locale.py` before it is sent (LANG-4), and the JavaScript reads the
same label dictionary from the embedded JSON.
"""

from __future__ import annotations

import json
import os

from ...shared import config
from . import locale, payload

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATE_NAME = "index.html"
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
}
_FALLBACK_TYPE = "application/octet-stream"


def static_path(name: str):
    """Absolute path of one static asset, or None when it escapes the folder."""
    base = os.path.abspath(STATIC_DIR)
    target = os.path.abspath(os.path.join(base, name))
    if not target.startswith(base + os.sep) or not os.path.isfile(target):
        return None
    return target


def static_body(name: str):
    """(content type, bytes) of one static asset, or None when it is missing."""
    target = static_path(name)
    if target is None:
        return None
    with open(target, "rb") as handle:
        data = handle.read()
    content_type = MIME_TYPES.get(os.path.splitext(target)[1], _FALLBACK_TYPE)
    return content_type, data


def read_template() -> str:
    """The HTML shell as stored on disk."""
    with open(os.path.join(STATIC_DIR, TEMPLATE_NAME), "r",
              encoding=config.ENCODING) as handle:
        return handle.read()


def render_page(template: str) -> str:
    """Fills the title, the labels and the version into the HTML shell."""
    labels = locale.labels()
    return (template
            .replace("{{TITLE}}", labels["app.title"])
            .replace("{{LABELS}}", json.dumps(labels, ensure_ascii=True))
            .replace("{{VERSION}}", payload.version_text()))
