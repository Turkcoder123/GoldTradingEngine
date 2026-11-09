"""Shared text table helpers: alignment, number formats, section rules.

Every section of the report prints aligned ASCII tables, so the layout lives
here once (MOD-1) instead of being copied per section.
"""

from __future__ import annotations

import re

_NUMERIC = re.compile(r"^[+-]?[\d,]+(\.\d+)?%?$")


def _is_numeric(values) -> bool:
    """True when every filled cell of a column looks like a number."""
    filled = [value for value in values if value not in ("", "-")]
    return bool(filled) and all(_NUMERIC.match(value) for value in filled)


def table(headers: list, rows: list) -> list:
    """Aligned table; a column of numbers is right aligned (CODE-8)."""
    widths = []
    for index, header in enumerate(headers):
        cells = [header] + [str(row[index]) for row in rows]
        widths.append(max(len(cell) for cell in cells))
    numeric = [_is_numeric([str(row[index]) for row in rows])
               for index in range(len(headers))]
    lines = [_row_text(headers, widths, numeric),
             "  ".join("-" * width for width in widths)]
    for row in rows:
        lines.append(_row_text([str(cell) for cell in row], widths, numeric))
    return lines


def _row_text(cells: list, widths: list, numeric: list) -> str:
    """One aligned line, with the trailing spaces removed."""
    parts = []
    for index, cell in enumerate(cells):
        width = widths[index]
        parts.append(cell.rjust(width) if numeric[index] else cell.ljust(width))
    return "  ".join(parts).rstrip()


def number(value, digits: int = 6) -> str:
    """Number with thousands separators and no trailing zeros ('-' for None)."""
    if value is None:
        return "-"
    text = f"{value:,.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def percent(value) -> str:
    """Signed percentage with two decimals ('-' for None)."""
    return "-" if value is None else f"{value:+.2f}%"


def signed(value, digits: int = 0) -> str:
    """Signed number with thousands separators ('-' for None)."""
    if value is None:
        return "-"
    return f"{value:+,.{digits}f}"


def age(minutes: int) -> str:
    """Compact age of the newest stored bar."""
    if minutes <= 0:
        return "-"
    if minutes < 120:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h"
    return f"{minutes // (24 * 60)} d"


def section(title: str) -> list:
    """Title plus a rule of the same length."""
    return ["", title, "-" * len(title)]
