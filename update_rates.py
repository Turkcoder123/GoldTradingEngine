#!/usr/bin/env python3
"""Entry point of the derived real interest rates.

The implementation lives in `src/`; this launcher only makes the documented
command work from the repository root:

    python update_rates.py                # fetch FRED series, rebuild the rates
    python update_rates.py --offline      # rebuild from the stored series only
    python update_rates.py --status       # what is stored, no network
    python update_rates.py --country US,DE

Real rate = long term government yield - consumer price inflation, both in
percent, joined on the month. See docs/rates.md.
"""

from __future__ import annotations

import sys

from src.features.cli.rates_app import main

if __name__ == "__main__":
    sys.exit(main())
