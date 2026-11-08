#!/usr/bin/env python3
"""Entry point for the CFTC Commitments of Traders export.

The implementation lives in `src/` (see README.md); this launcher only makes
`python update_cot.py` work from the repository root:

    python update_cot.py                  # current year, COMEX gold only
    python update_cot.py --year 2025      # an older archive
    python update_cot.py --all-gold       # every market containing GOLD
"""

from __future__ import annotations

import sys

from src.features.cli.cot_app import main

if __name__ == "__main__":
    sys.exit(main())
