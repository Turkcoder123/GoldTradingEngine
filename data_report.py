#!/usr/bin/env python3
"""Entry point of the stored-data text report.

The implementation lives in `src/features/report/`; this launcher only makes the
documented command work from the repository root:

    python data_report.py                  # <data dir>/data_report.txt
    python data_report.py --output -       # print it instead
    python data_report.py --output report.txt

The report is a read-only inventory of the CSV files: assets, last values, the
resolution of the stored rows and the covered time range.
"""

from __future__ import annotations

import sys

from src.features.report.app import main

if __name__ == "__main__":
    sys.exit(main())
