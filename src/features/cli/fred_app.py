"""Command line for the FRED macro series: arguments, wiring and reporting."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ...core import fred
from ...shared import config, version


def _series_argument(value: str) -> list:
    """'DGS10,DFII10' -> ['DGS10', 'DFII10'], keeping only known ids."""
    wanted = [item.strip().upper()
              for item in value.split(",") if item.strip()]
    unknown = [item for item in wanted if item not in config.FRED_SERIES]
    if not wanted or unknown:
        raise argparse.ArgumentTypeError(
            f"unknown series {', '.join(unknown) or value!r}; "
            f"known ids: {', '.join(sorted(config.FRED_SERIES))}")
    return wanted


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="update_fred.py",
        description="Downloads FRED macro series (keyless CSV endpoint) and "
                    "stores them as date,value CSV files.")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--series", type=_series_argument, default=None,
        help="comma separated FRED ids (default: the registered set)")
    parser.add_argument(
        "--status", action="store_true",
        help="summarize the stored series and exit (no network)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    try:
        version_text = version.read_version()
    except version.VersionError as exc:
        version_text = f"unknown version ({exc})"
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {version_text}")
    return parser


def format_summary(series_id: str, summary: fred.FredSummary) -> str:
    """One line per series: latest value, short and yearly change."""
    label = config.FRED_SERIES.get(series_id, "unknown series")
    if summary.date is None or summary.value is None:
        return f"   {series_id:<8} no observations ({label})"
    text = f"   {series_id:<8} {summary.date} {summary.value:>12,.3f}"
    if summary.change is not None:
        text += f" | change {summary.change:+,.3f}"
    if summary.year_change is not None:
        text += f" | 1y {summary.year_change:+,.3f}"
    return f"{text}  ({label})"


def format_result(result: fred.FredResult) -> str:
    """Multi-line summary of an update: file count plus one line per series."""
    if not result.ok:
        return f" ! FRED update failed: {result.error}"
    total = sum(result.counts.values())
    lines = [f" +{len(result.files)} FRED series ({total:,} observations)"]
    for series_id, summary in sorted(result.summaries.items()):
        lines.append(format_summary(series_id, summary))
    return "\n".join(lines)


def format_status(summaries: dict) -> list:
    """Offline summary of the stored series, one line each."""
    if not summaries:
        return [" ! no stored FRED series (run without --status to download)"]
    lines = [f" FRED (as stored, {len(summaries)} series)"]
    for series_id, summary in sorted(summaries.items()):
        lines.append(format_summary(series_id, summary))
    return lines


def _json_payload(result: fred.FredResult) -> str:
    """Result as JSON, with the summaries as plain dicts."""
    payload = asdict(result)
    payload["ok"] = result.ok
    payload["summaries"] = {name: summary.to_dict()
                            for name, summary in result.summaries.items()}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)

    if args.status:
        summaries = fred.status(data_dir, args.series)
        if args.json:
            print(json.dumps({name: summary.to_dict()
                              for name, summary in summaries.items()},
                             indent=2, ensure_ascii=False))
        else:
            for line in format_status(summaries):
                print(line)
        return 0 if summaries else 1

    result = fred.update_fred(data_dir, args.series)
    if args.json:
        print(_json_payload(result))
    elif not args.quiet or not result.ok:
        print(format_result(result))
    return 0 if result.ok else 1
