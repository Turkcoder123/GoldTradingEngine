"""Command line for the derived real interest rates (FRED based).

`update_rates.py` downloads the long term yield and the inflation series of
each country, then rebuilds one `real_<cc>.csv` per country plus the summary the
report and the dashboard read.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from ...core import rates
from ...shared import config, version


def _country_argument(value: str) -> list:
    """'US,DE' -> ['US', 'DE'], rejecting unknown country codes."""
    wanted = [item.strip().upper() for item in value.split(",") if item.strip()]
    unknown = [item for item in wanted if item not in config.RATES_COUNTRIES]
    if not wanted or unknown:
        raise argparse.ArgumentTypeError(
            f"unknown country {', '.join(unknown) or value!r}, expected one of "
            f"{', '.join(sorted(config.RATES_COUNTRIES))}")
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
        prog="update_rates.py",
        description="Derives real interest rates (long term yield minus CPI "
                    "inflation) from FRED and stores them as CSV files.")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--country", type=_country_argument, default=None,
        help="comma separated country codes, for example US,DE "
             "(default: every registered country)")
    parser.add_argument(
        "--offline", action="store_true",
        help="rebuild the derived files from the stored FRED series only")
    parser.add_argument(
        "--status", action="store_true",
        help="summarize the stored rates and exit (no network)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    parser.add_argument("--version", action="version",
                        version=_version_text())
    return parser


def format_country(code: str, described: dict) -> str:
    """One line per country: latest real rate, its date and the yearly change."""
    latest = described.get("latest")
    change = described.get("change_1y")
    marker = "  STALE" if described.get("stale") else ""
    return ("   %-3s %-16s %-10s %8s  1y %s%s" % (
        code, described.get("label", "-")[:16],
        described.get("last_date") or "-",
        f"{latest:+.3f}" if latest is not None else "-",
        f"{change:+.3f}" if change is not None else "-", marker))


def format_result(result: rates.RatesResult, world: dict) -> str:
    """Multi-line summary of an update, with the median across countries."""
    if not result.ok:
        return f" ! rates update failed: {result.error}"
    lines = [f" +{len(result.countries)} real rate series"]
    for code, described in result.countries.items():
        lines.append(format_country(code, described))
    median = world.get("median")
    lines.append("   world median %s over %d countries" % (
        f"{median:+.3f}" if median is not None else "-", world.get("count", 0)))
    lines.extend(f" ! {warning}" for warning in result.warnings)
    return "\n".join(lines)


def format_status(body: dict) -> list:
    """Offline summary of the stored real rate series."""
    countries = body["countries"]
    stored = {code: described for code, described in countries.items()
              if described["rows"]}
    if not stored:
        return [" ! no stored real rates (run without --status to build them)"]
    lines = [f" real interest rates (derived, {len(stored)} countries)"]
    for code, described in stored.items():
        lines.append(format_country(code, described))
    world = body["world"]
    median = world.get("median")
    lines.append("   world median %s over %d countries" % (
        f"{median:+.3f}" if median is not None else "-", world.get("count", 0)))
    return lines


def _payload(result: rates.RatesResult, body: dict) -> str:
    """JSON answer with the result and the world summary."""
    document = asdict(result)
    document["ok"] = result.ok
    document["world"] = {key: value for key, value in body["world"].items()
                         if key != "points"}
    return json.dumps(document, indent=2, ensure_ascii=False)


def main(argv=None) -> int:
    """Command line entry point: 0 on success, 1 on a real failure."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    if args.status:
        body = rates.status(data_dir)
        stored = any(described["rows"] for described in body["countries"].values())
        if args.json:
            print(json.dumps({"countries": body["countries"],
                              "world": {key: value
                                        for key, value in body["world"].items()
                                        if key != "points"}},
                             indent=2, ensure_ascii=False))
        else:
            for line in format_status(body):
                print(line)
        return 0 if stored else 1
    result = rates.update_rates(data_dir, args.country,
                                refresh=not args.offline)
    body = rates.status(data_dir)
    if args.json:
        print(_payload(result, body))
    elif not args.quiet or not result.ok:
        print(format_result(result, body["world"]))
    return 0 if result.ok and result.countries else 1
