"""Command line of the stored-data report: gather, render, write one file.

The report is a snapshot of the CSV files, so it never downloads and never
changes them; `--output -` prints it instead of writing the default file inside
the data directory.
"""

from __future__ import annotations

import argparse
import os
import sys

from ...shared import config, version
from . import collect, locale, render

DEFAULT_NAME = "data_report.txt"


def _version_text() -> str:
    """--version output; warns when VERSION cannot be read."""
    try:
        return f"%(prog)s {version.read_version()}"
    except version.VersionError as exc:
        return f"%(prog)s unknown version ({exc})"


def build_parser() -> argparse.ArgumentParser:
    """The complete command line definition."""
    parser = argparse.ArgumentParser(
        prog="data_report.py",
        description="Writes a plain text inventory of the stored price, COT "
                    "and macro data (standard library only, offline).")
    parser.add_argument(
        "--data-dir", default=None,
        help="data directory (default: $XAUUSD_DATA_DIR or "
             "<project>/xauusd_data)")
    parser.add_argument(
        "--output", default=None,
        help="file to write (default: <data dir>/" + DEFAULT_NAME +
             "; '-' prints to stdout)")
    parser.add_argument(
        "--year", type=int, default=None,
        help="COT year (default: the newest stored year)")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    parser.add_argument("--version", action="version",
                        version=_version_text())
    return parser


def output_path(args, data_dir: str) -> str:
    """--output, or the default file inside the data directory."""
    if args.output:
        return args.output
    return os.path.join(data_dir, DEFAULT_NAME)


def write_report(path: str, text: str) -> None:
    """Writes the report and creates its folder; OSError reaches the caller."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding=config.ENCODING, newline="\n") as handle:
        handle.write(text)


def main(argv=None) -> int:
    """Command line entry point: 0 when the report is written, 1 otherwise."""
    args = build_parser().parse_args(argv)
    data_dir = config.resolve_data_dir(args.data_dir)
    document = collect.build(data_dir, args.year)
    text = render.render(document, locale.labels(), locale.notes())
    if args.output == "-":
        print(text, end="")
        return 0
    path = output_path(args, data_dir)
    try:
        write_report(path, text)
    except OSError as exc:
        print(f" ! cannot write {path}: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f" + data report: {path} ({len(text.splitlines())} lines)")
    return 0
