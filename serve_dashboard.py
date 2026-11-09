#!/usr/bin/env python3
"""Entry point of the local data dashboard.

The implementation lives in `src/features/web/`; this launcher only makes the
documented command work from the repository root:

    python serve_dashboard.py               # http://127.0.0.1:8765/
    python serve_dashboard.py --port 9000   # another port
    python serve_dashboard.py --help        # every option

The page is read-only: it shows what the updaters stored and never downloads. A
PID file in the data directory keeps a second start on the same address from
happening by accident; `--no-pid` skips that check.
"""

from __future__ import annotations

import sys

from src.features.web.cli import main

if __name__ == "__main__":
    sys.exit(main())
