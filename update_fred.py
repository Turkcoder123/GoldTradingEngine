#!/usr/bin/env python3
"""Entry point for the FRED macro series.

The implementation lives in `src/` (see README.md); no API key is needed:

    python update_fred.py                    # the registered series
    python update_fred.py --series DGS10,DFII10
    python update_fred.py --status           # summarize what is stored
"""

from __future__ import annotations

import sys

from src.features.cli.fred_app import main

if __name__ == "__main__":
    sys.exit(main())
