"""Command line for the CFTC COT exports: arguments, wiring and reporting."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict

from ...core import cot
from ...shared import config, version


def _add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--year", type=int, default=None,
        help="report year (default: the current UTC year)")
    parser.add_argument(
        "--all-gold", action="store_true",
        help="keep every market whose name contains GOLD "
             "(default: only COMEX gold)")
    parser.add_argument(
        "--status", action="store_true",
        help="summarize the stored COT files and exit (no network)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="update_cot.py",
        description="Downloads the CFTC Commitments of Traders archives and "
                    "stores the COMEX gold positioning as CSV "
                    "(standard library only).")
    _add_options(parser)
    try:
        version_text = version.read_version()
    except version.VersionError as exc:
        version_text = f"unknown version ({exc})"
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {version_text}")
    return parser


def format_summary(label: str, summary: cot.CotSummary) -> str:
    """One readable line: net position, share of OI and the two changes."""
    if summary.date is None:
        return f"   {label:<8} no data"
    return (f"   {label:<8} {summary.date} | OI {summary.open_interest:,}"
            f" | net {summary.net:+,} ({summary.net_share:.1%} of OI)"
            f" | week {summary.weekly_change:+,}"
            f" | {summary.trend_weeks}w {summary.trend_change:+,}")


def format_result(result: cot.CotResult) -> str:
    """Multi-line summary of an update: files plus one line per report."""
    if not result.ok:
        return f" ! COT update failed: {result.error}"
    files = ", ".join(f"{name} ({count} rows)"
                      for name, count in sorted(result.counts.items()))
    lines = [f" +{result.year} COT gold: {files}"]
    for report, summary in sorted(result.summaries.items()):
        lines.append(format_summary(report, summary))
    return "\n".join(lines)


def format_status(reports: dict, year: int) -> list:
    """Offline summary of the stored reports, one line each."""
    if not reports:
        return [f" ! no stored COT files for {year} "
                f"(run without --status to download them)"]
    lines = [f" COT {year} (as stored)"]
    for report, summary in sorted(reports.items()):
        lines.append(format_summary(report, summary))
    return lines


def _json_payload(result: cot.CotResult) -> str:
    """Result as JSON, including the derived share of open interest."""
    payload = asdict(result)
    payload["ok"] = result.ok
    payload["summaries"] = {name: summary.to_dict()
                            for name, summary in result.summaries.items()}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    year = args.year or dt.datetime.now(dt.timezone.utc).year

    if args.status:
        reports = cot.status(data_dir, year)
        if args.json:
            print(json.dumps(
                {name: summary.to_dict() for name, summary in
                 reports.items()}, indent=2, ensure_ascii=False))
        else:
            for line in format_status(reports, year):
                print(line)
        return 0 if reports else 1

    result = cot.update_cot(data_dir, year, all_gold=args.all_gold)
    if args.json:
        print(_json_payload(result))
    elif not args.quiet or not result.ok:
        print(format_result(result))
    return 0 if result.ok else 1
