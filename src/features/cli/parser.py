"""Command line surface: argument definitions only, no side effects."""

from __future__ import annotations

import argparse

from ...shared import config, timeutil, version

_DESCRIPTION = (
    "Standalone 1-minute data keeper (gold complex, DXY): keeps the monthly "
    "CSVs current from the Dukascopy web service (standard library only).")
_EPILOG = (
    "Examples:\n"
    "  python update_1m.py                     fill the gap once\n"
    "  python update_1m.py --loop              keep it current\n"
    "  python update_1m.py --status            freshness, no network\n"
    "  python update_1m.py --since 2020-01-01  bootstrap from a date\n")


def _date_argument(value: str):
    """argparse adapter around timeutil.parse_cli_date."""
    try:
        return timeutil.parse_cli_date(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def version_text() -> str:
    """--version output; warns when VERSION cannot be read."""
    try:
        return f"%(prog)s {version.read_version()}"
    except version.VersionError as exc:
        return f"%(prog)s unknown version ({exc})"


def _add_data_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--lock-dir", default=None,
        help="where the lock file lives (default: $XAUUSD_LOCK_DIR or "
             "the data dir)")
    parser.add_argument(
        "--series", type=str.lower, choices=sorted(config.SERIES),
        default=config.DEFAULT_SERIES,
        help="price series to keep (default %(default)s)")
    parser.add_argument(
        "--offer-side", type=str.upper, choices=list(config.SIDES),
        default=config.DEFAULT_SIDE,
        help="B = BID (default), A = ASK; each side has its own files")


def _add_feed_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--segment-hours", type=int, default=config.DEFAULT_SEGMENT_HOURS,
        help="hours of gap per request (default %(default)s)")
    parser.add_argument(
        "--segments", type=int, default=config.DEFAULT_SEGMENTS,
        help="max requests per run (default %(default)s)")
    parser.add_argument(
        "--empty-allowance-hours", type=int,
        default=config.DEFAULT_EMPTY_ALLOWANCE_HOURS,
        help="hours without bars accepted as a market closure before a "
             "run stops (default %(default)s)")
    parser.add_argument(
        "--since", type=_date_argument, default=None,
        help="first bar when no history exists yet (YYYY-MM-DD)")
    parser.add_argument(
        "--timeout", type=float, default=config.DEFAULT_TIMEOUT_SECONDS,
        help="per-request timeout in seconds (default %(default)s)")


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--loop", action="store_true",
        help="keep running, refresh every --interval minutes")
    parser.add_argument(
        "--interval", type=float, default=config.DEFAULT_INTERVAL_MINUTES,
        help="minutes between refreshes in --loop (default %(default)s)")
    parser.add_argument(
        "--no-lock", action="store_true",
        help="skip the single-instance lock (not recommended)")


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--status", action="store_true",
        help="print the freshness report and exit (no network)")
    parser.add_argument(
        "--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--quiet", action="store_true",
        help="only print failures and real updates")
    parser.add_argument(
        "--version", action="version", version=version_text())


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="update_1m.py",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    _add_data_options(parser)
    _add_feed_options(parser)
    _add_run_options(parser)
    _add_output_options(parser)
    return parser
