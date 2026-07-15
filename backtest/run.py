#!/usr/bin/env python3
"""Convenience entrypoint: python backtest/run.py --fast

Same as ``python -m backtest``. Adds the repo root to PYTHONPATH automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
