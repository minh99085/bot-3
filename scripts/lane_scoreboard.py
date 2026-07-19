#!/usr/bin/env python3
"""Print the paired lane scoreboard from lane ledgers.

    PYTHONPATH=. python3 scripts/lane_scoreboard.py --root data/paper
    PYTHONPATH=. python3 scripts/lane_scoreboard.py --root reports/paper_ledger_export
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.lane_compare import board_from_ledgers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="data/paper")
    ap.add_argument("--out", default="reports/lane_scoreboard.txt")
    args = ap.parse_args(argv)

    board = board_from_ledgers(args.root)
    text = board.text()
    print(text)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n")
    print(f"\n[written → {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
