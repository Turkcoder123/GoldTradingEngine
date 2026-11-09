"""Command line for the alternative sources: ETF gold, GVZ and Fed documents.

One entry point for the three context sources keeps the root of the repository
small; each source keeps its own storage module under `core/`.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from ...core import etf, fedtext, gvz
from ...shared import config, version

SOURCES = ("etf", "gvz", "fed")


def _etf_argument(value: str) -> list:
    """'gld,iau' -> ['gld', 'iau'], rejecting unknown fund keys."""
    wanted = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in wanted if item not in config.ETF_SERIES]
    if not wanted or unknown:
        raise argparse.ArgumentTypeError(
            f"unknown fund {', '.join(unknown) or value!r}, expected one of "
            f"{', '.join(sorted(config.ETF_SERIES))}")
    return wanted


def _version_text() -> str:
    """--version output; warns when VERSION cannot be read."""
    try:
        return f"%(prog)s {version.read_version()}"
    except version.VersionError as exc:
        return f"%(prog)s unknown version ({exc})"


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="update_alt.py",
        description="Downloads the alternative market context sources (ETF gold "
                    "holdings, Cboe GVZ, Federal Reserve documents) and stores "
                    "them as CSV under <data dir>/alt (standard library only).")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--source", action="append", choices=SOURCES, default=None,
        help="source to update, repeatable (default: all of them)")
    parser.add_argument(
        "--etf", type=_etf_argument, default=None,
        help="comma separated fund keys for --source etf (default: all)")
    parser.add_argument(
        "--limit", type=int, default=config.ALT_LIMIT_DOCUMENTS,
        help="newest Fed documents fetched per run (default %(default)s)")
    parser.add_argument(
        "--status", action="store_true",
        help="summarize what is stored and exit (no network)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    parser.add_argument("--version", action="version",
                        version=_version_text())
    return parser


def _value(latest) -> str:
    """Latest stored value as text, with thousands separators for numbers."""
    if isinstance(latest, float):
        return f"{latest:,.2f}"
    return "-" if latest is None else str(latest)


def _describe(described: dict, value_label: str) -> str:
    """One line for a stored series: coverage, rows and the latest value."""
    name = os.path.basename(str(described.get("file") or "-"))
    return (f" {name:<20}"
            f"{described.get('rows', 0):>7,} rows"
            f"  {described.get('first_date') or '-'} -> "
            f"{described.get('last_date') or '-'}"
            f"  | {value_label} {_value(described.get('latest'))}")


def format_etf(result: etf.EtfResult) -> str:
    """One line per fund, plus the error when the run failed."""
    if not result.ok:
        return f" ! ETF update failed: {result.error}"
    lines = [f" +{len(result.series)} ETF series"]
    for key, described in sorted(result.series.items()):
        lines.append(_describe(described, "tonnes"))
    return "\n".join(lines)


def format_gvz(result: gvz.GvzResult) -> str:
    """One line for the volatility index."""
    if not result.ok:
        return f" ! GVZ update failed: {result.error}"
    described = {"file": result.file, "rows": result.rows,
                 "first_date": result.first_date,
                 "last_date": result.last_date, "latest": result.latest}
    return " +1 volatility series" + _describe(described, "close")


def format_fed(result: fedtext.FedResult) -> str:
    """One line for the document index."""
    if not result.ok:
        return f" ! Fed update failed: {result.error}"
    return (f" +{result.added} documents  {result.file}"
            f"  ({result.total} stored, newest {result.latest or '-'})")


def format_status(store: dict) -> list:
    """Offline summary of every stored alternative source."""
    lines = [" alternative sources"]
    for key, described in sorted(store["etf"].items()):
        lines.append(_describe(described, "tonnes"))
    lines.append(_describe(store["gvz"], "close"))
    fed_status = store["fed"]
    lines.append(f" {'fed':<20}{fed_status['rows']:>7,} rows"
                 f"  {fed_status['first_date'] or '-'} -> "
                 f"{fed_status['last_date'] or '-'}"
                 f"  | texts {fed_status['texts']}")
    return lines


def _run(args, data_dir: str) -> dict:
    """Runs the requested sources and returns their results."""
    results = {}
    for source in args.source or SOURCES:
        if source == "etf":
            results[source] = etf.update_etf(data_dir, args.etf)
        elif source == "gvz":
            results[source] = gvz.update_gvz(data_dir)
        else:
            results[source] = fedtext.update_fed(data_dir, args.limit)
    return results


def _report(results: dict, args) -> None:
    """Prints the result of every source, or one JSON document."""
    if args.json:
        print(json.dumps({name: dict(asdict(result), ok=result.ok)
                          for name, result in results.items()},
                         indent=2, ensure_ascii=False))
        return
    formatters = {"etf": format_etf, "gvz": format_gvz, "fed": format_fed}
    for name, result in results.items():
        if result.ok and args.quiet:
            continue
        print(formatters[name](result))


def _status(data_dir: str) -> tuple:
    """Stored sources and whether anything is stored at all."""
    store = {"etf": etf.status(data_dir), "gvz": gvz.status(data_dir),
             "fed": fedtext.status(data_dir)}
    stored = (any(item["rows"] for item in store["etf"].values())
              or bool(store["gvz"]["rows"]) or bool(store["fed"]["rows"]))
    return store, stored


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    if args.status:
        store, stored = _status(data_dir)
        if args.json:
            print(json.dumps(store, indent=2, ensure_ascii=False))
        else:
            for line in format_status(store):
                print(line)
        return 0 if stored else 1
    results = _run(args, data_dir)
    _report(results, args)
    return 0 if all(result.ok for result in results.values()) else 1
