#!/usr/bin/env python3
"""Entry point of the XAU/USD 1-minute data keeper.

The implementation lives in `src/` (rules.md MOD-2 keeps every module small and
single purpose); this launcher only makes the documented command work from the
repository root, which is also what cron runs:

    */15 * * * * cd /path/to/repo && python update_1m.py --quiet

Usage, options, data format and layout are documented in README.md.
"""

from __future__ import annotations

import sys

from src.features.cli.app import main

if __name__ == "__main__":
    sys.exit(main())
