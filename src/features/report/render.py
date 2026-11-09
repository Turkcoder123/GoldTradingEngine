"""Text layout of the stored-data report: aligned tables plus a legend.

The report is plain ASCII so it survives any terminal, mail client or paste
(LANG-3); every label comes from `locale.py` and every value from `collect.py`.
"""

from __future__ import annotations

import textwrap

from . import render_alt
from .render_table import age, number, percent, section, signed, table

_FIELD = 15


def _header(document: dict, labels: dict) -> list:
    """Report title and the four lines that identify the data set."""
    totals = document["totals"]
    coverage = labels["totals.value"].format(
        series=totals["series"], files=totals["files"],
        bars=number(totals["bars"]), size=number(totals["size_mb"], 2),
        first=totals["first_bar"] or "-", last=totals["last_bar"] or "-")
    return [
        labels["title"],
        "=" * len(labels["title"]),
        f"{labels['generated']:<{_FIELD}}: {document['generated_at']} UTC",
        f"{labels['version']:<{_FIELD}}: {document['version']}",
        f"{labels['data_dir']:<{_FIELD}}: {document['data_dir']}",
        f"{labels['totals']:<{_FIELD}}: {coverage}",
    ]


def _price_coverage(document: dict, labels: dict) -> list:
    """What is stored per price series: coverage and volume."""
    headers = [labels["prices." + name] for name in
               ("series", "instrument", "frequency", "first_bar", "last_bar",
                "days", "bars", "files", "size")]
    rows = []
    for row in document["prices"]:
        rows.append([
            row["key"], row["instrument"], row["frequency"],
            row["first_bar"] or "-", row["last_bar"] or "-",
            number(row["days"]), number(row["bars"]), number(row["files"]),
            number(row["size_mb"], 2),
        ])
    return section(labels["prices.coverage.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def _price_latest(document: dict, labels: dict) -> list:
    """Latest close, the two changes and the freshness of every series."""
    headers = [labels["prices." + name] for name in
               ("series", "last_close", "day_change", "range_change", "age")]
    rows = []
    for row in document["prices"]:
        rows.append([
            row["key"], number(row["last_close"]),
            percent(row["day_change_pct"]), percent(row["range_change_pct"]),
            age(row["age_minutes"]),
        ])
    return section(labels["prices.latest.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def _cot(document: dict, labels: dict) -> list:
    """Weekly positioning: coverage, open interest, net and the two changes."""
    headers = [labels["cot." + name] for name in
               ("report", "frequency", "first", "last", "reports",
                "open_interest", "net", "share", "week_change",
                "trend_change")]
    rows = []
    for row in document["cot"]["rows"]:
        rows.append([
            labels["cot." + row["report"]], row["frequency"],
            row["first_date"] or "-", row["last_date"] or "-",
            number(row["reports"]), number(row["open_interest"]),
            signed(row["net"]), f"{row['net_share'] * 100:.1f}%",
            signed(row["weekly_change"]), signed(row["trend_change"]),
        ])
    return section(labels["cot.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def _macro(document: dict, labels: dict) -> list:
    """Every stored macro series with its unit, frequency and last value."""
    headers = [labels["macro." + name] for name in
               ("id", "what", "unit", "frequency", "first", "last",
                "observations", "latest", "change", "year_change")]
    rows = []
    for row in document["macro"]:
        rows.append([
            row["id"], row["label"], row["unit"], row["frequency"],
            row["first_date"] or "-", row["last_date"] or "-",
            number(row["observations"]), number(row["value"]),
            signed(row["change"], 3), signed(row["year_change"], 3),
        ])
    return section(labels["macro.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def _rates(document: dict, labels: dict) -> list:
    """Derived real rates per country plus the equal weighted median."""
    body = document["rates"]
    stored = {code: described for code, described in
              body["countries"].items() if described["rows"]}
    if not stored:
        return section(labels["rates.title"]) + [labels["nothing"]]
    headers = [labels[name] for name in
               ("rates.country", "rates.name", "rates.last", "rates.latest",
                "rates.change", "rates.rows")]
    rows = [[code, described["label"], described["last_date"] or "-",
             f"{described['latest']:+.3f}"
             if described["latest"] is not None else "-",
             f"{described['change_1y']:+.3f}"
             if described["change_1y"] is not None else "-",
             number(described["rows"])]
            for code, described in stored.items()]
    world = body["world"]
    median = world.get("median")
    lines = section(labels["rates.title"]) + table(headers, rows)
    lines.append(labels["rates.world"].format(
        median=f"{median:+.3f}" if median is not None else "-",
        count=world.get("count", 0)))
    stale = [code for code, described in stored.items() if described.get("stale")]
    if stale:
        lines.append(labels["rates.stale"].format(countries=", ".join(stale)))
    return lines


def _legend(labels: dict, notes: tuple, width: int = 96) -> list:
    """Legend lines, wrapped so the file stays readable on a narrow screen."""
    if not notes:
        return []
    lines = section(labels["notes"])
    for note in notes:
        lines.extend(textwrap.wrap(note, width=width) or [""])
    return lines


def render(document: dict, labels: dict, notes: tuple = ()) -> str:
    """The complete report as one ASCII string, newline terminated."""
    lines = _header(document, labels)
    lines += _price_coverage(document, labels)
    lines += _price_latest(document, labels)
    lines += _cot(document, labels)
    lines += _macro(document, labels)
    lines += render_alt.etf_section(document, labels)
    lines += render_alt.volatility_section(document, labels)
    lines += render_alt.fed_section(document, labels)
    lines += _rates(document, labels)
    lines += _legend(labels, notes)
    return "\n".join(lines) + "\n"
