"""CLI entry: python -m backtest …"""

from __future__ import annotations

import sys

from backtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
