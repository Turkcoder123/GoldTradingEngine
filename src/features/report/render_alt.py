"""Text sections of the alternative sources: ETF tonnage, GVZ, Fed documents."""

from __future__ import annotations

from .render_table import number, section, table


def etf_section(document: dict, labels: dict) -> list:
    """Gold ETF tonnage per stored fund."""
    headers = [labels[name] for name in
               ("etf.fund", "etf.source", "common.rows", "common.first",
                "common.last", "etf.tonnes")]
    rows = [[row["key"], row["source"], number(row["rows"]),
             row["first_date"] or "-", row["last_date"] or "-",
             number(row["tonnes"], 2)] for row in document["etf"]]
    return section(labels["etf.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def volatility_section(document: dict, labels: dict) -> list:
    """The stored volatility index."""
    headers = [labels[name] for name in
               ("volatility.index", "common.rows", "common.first",
                "common.last", "volatility.close")]
    rows = [[row["key"], number(row["rows"]), row["first_date"] or "-",
             row["last_date"] or "-", number(row["close"], 2)]
            for row in document["volatility"] if row["rows"]]
    return section(labels["volatility.title"]) + (
        table(headers, rows) if rows else [labels["nothing"]])


def fed_section(document: dict, labels: dict) -> list:
    """Document counts per kind, with the total size of the stored texts."""
    fed = document["fed"]
    if not fed["rows"]:
        return section(labels["fed.title"]) + [labels["nothing"]]
    headers = [labels["fed.kind"], labels["fed.count"]]
    rows = [[kind, number(count)]
            for kind, count in sorted(fed["kinds"].items())]
    lines = section(labels["fed.title"]) + table(headers, rows)
    lines.append(labels["fed.summary"].format(
        rows=number(fed["rows"]), texts=number(fed["texts"]),
        chars=number(fed["chars"]), first=fed["first_date"] or "-",
        last=fed["last_date"] or "-"))
    return lines
