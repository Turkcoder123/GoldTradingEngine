#!/usr/bin/env python3
"""Entry point of the temporary Twelve Data live stream.

The implementation lives in `src/core/live_*.py` and `src/features/cli/`;
this launcher only makes the documented command work from the repository root:

    python stream_live.py                  # stream until interrupted
    python stream_live.py --seconds 60     # bounded run
    python stream_live.py --json           # one JSON object per closed bar

The stream is memory-only: it never appends to the stored CSV history, and the
Dukascopy keeper stays the authority (`docs/live.md`).
"""

from __future__ import annotations

import sys

from src.features.cli.live_app import main

if __name__ == "__main__":
    sys.exit(main())
