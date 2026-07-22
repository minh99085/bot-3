#!/usr/bin/env python3
"""C1 — pull live Polymarket btc15 books, compute the $/week capacity ceiling.

Run on the VPS (needs Polymarket reachability):

    PYTHONPATH=. python3 scripts/capacity_report.py --root data/paper

Writes reports/capacity_ceiling.txt. The number is the MOST the strategy can
deploy per week at no-price-impact sizes — judge the prize against the effort.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.capacity import estimate_capacity, estimate_signal_rate  # noqa: E402
from backtest.paper_ledger import load_trades  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="data/paper")
    ap.add_argument("--out", default="reports/capacity_ceiling.txt")
    args = ap.parse_args(argv)

    from connectors.polymarket import PolymarketClient

    pm = PolymarketClient()
    markets = pm.list_scoped_updown_markets()
    target = next(
        (m for m in markets if "btc" in (m.slug or "").lower() and m.timeframe == "15m"),
        None,
    )
    if target is None:
        print("no live btc 15m market found in scope")
        return 2
    raw = target.raw or {}
    yes_token = raw.get("yes_token_id")
    no_token = raw.get("no_token_id")
    if not yes_token or not no_token:
        print(f"market {target.slug} lacks CLOB token ids")
        return 2

    def asks(token_id: str) -> list[tuple[float, float]]:
        book = pm.get_orderbook(str(token_id))
        return [(lvl.price, lvl.size) for lvl in book.asks]

    yes_asks = asks(yes_token)
    no_asks = asks(no_token)

    ledgers = sorted(Path(args.root).glob("*/trade_ledger.jsonl"))
    trades = load_trades(ledgers)
    rate = estimate_signal_rate([t.window_ts for t in trades])

    est = estimate_capacity(yes_asks, no_asks, signal_rate=rate)
    text = (
        f"market: {target.slug}\n"
        f"book depth sampled: YES {len(yes_asks)} ask levels, "
        f"NO {len(no_asks)} ask levels\n\n" + est.text()
    )
    print(text)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n")
    print(f"\n[written → {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
