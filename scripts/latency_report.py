#!/usr/bin/env python3
"""A2 — fleet stale_edge_rate from latency_probe.jsonl.

If PM already repriced on most signals, there is NO capturable edge and A3
(barrier eval) is moot regardless of prediction quality.

    PYTHONPATH=. python3 scripts/latency_report.py --root data/paper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes.latency_probe import stale_edge_rate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="data/paper")
    ap.add_argument("--min-dislocation", type=float, default=0.05)
    args = ap.parse_args(argv)

    rows: list[dict] = []
    for f in sorted(Path(args.root).glob("*/latency_probe.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not rows:
        print(f"no latency_probe.jsonl rows under {args.root}/*/")
        return 2

    agg = stale_edge_rate(rows, min_dislocation=args.min_dislocation)
    print("=== A2 latency / stale-edge report ===")
    print(f"probe rows: {len(rows)}  (|dislocation|>={args.min_dislocation})")
    print(f"considered: {agg['n']}")
    if agg["n"]:
        print(f"stale_edge_rate: {agg['stale_edge_rate']:.1%}")
        print(f"pm_agrees_rate:  {agg['pm_agrees_rate']:.1%}")
        print(f"VERDICT: {agg['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
