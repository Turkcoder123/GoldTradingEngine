#!/usr/bin/env python3
"""Entry point of the alternative market context sources.

The implementation lives in `src/`; this launcher only makes the documented
command work from the repository root:

    python update_alt.py                  # ETF gold, GVZ and Fed documents
    python update_alt.py --source gvz     # one source only
    python update_alt.py --status         # what is stored, no network

Sources: SPDR Gold Shares archive (XLSX), iShares product page, Cboe GVZ history
and the Federal Reserve RSS feeds. See docs/alternative.md.
"""

from __future__ import annotations

import sys

from src.features.cli.alt_app import main

if __name__ == "__main__":
    sys.exit(main())
