#!/usr/bin/env python3
"""Pull resolved Polymarket crypto up/down markets + CLOB price history.

Run anywhere with network access to gamma-api.polymarket.com and
clob.polymarket.com (VPS, or a Claude session whose environment allowlists
them). Writes an immutable cache consumed offline by backtest.gamma_corpus:

    data/cache/gamma/pages/markets_page_NNNN.json
    data/cache/gamma/prices/<up_token_id>.json
    data/cache/gamma/manifest.json

Usage:
    PYTHONPATH=. python3 scripts/pull_gamma_corpus.py \
        --max-markets 2000 --max-pages 400 --with-prices

The pull is resumable: existing pages/price files are kept; re-running
continues from the next page offset and only fetches missing price files.
After pulling, print the approval sample with:
    PYTHONPATH=. python3 -c "from backtest.gamma_corpus import sample_report; print(sample_report())"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.gamma_corpus import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    parse_updown_market,
)

logger = logging.getLogger("pull_gamma_corpus")

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CLOB_PRICES = "https://clob.polymarket.com/prices-history"
PAGE_LIMIT = 100


def pull_market_pages(
    cache: Path,
    *,
    max_markets: int,
    max_pages: int,
    client: httpx.Client,
    sleep_sec: float,
) -> int:
    """Page /markets (closed, newest first), keep raw pages, count in-scope."""
    pages_dir = cache / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(pages_dir.glob("markets_page_*.json"))
    start_page = len(existing)
    n_in_scope = sum(
        1
        for f in existing
        for row in json.loads(f.read_text())
        if parse_updown_market(row) is not None
    )
    logger.info("resuming at page %d (in-scope so far: %d)", start_page, n_in_scope)

    for page_i in range(start_page, max_pages):
        if n_in_scope >= max_markets:
            break
        params = {
            "closed": "true",
            "limit": PAGE_LIMIT,
            "offset": page_i * PAGE_LIMIT,
            "order": "endDate",
            "ascending": "false",
        }
        r = client.get(GAMMA_MARKETS, params=params)
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            logger.info("no more rows at page %d", page_i)
            break
        (pages_dir / f"markets_page_{page_i:04d}.json").write_text(json.dumps(rows))
        hits = sum(1 for row in rows if parse_updown_market(row) is not None)
        n_in_scope += hits
        logger.info(
            "page %d: %d rows, %d in-scope (total %d)", page_i, len(rows), hits, n_in_scope
        )
        time.sleep(sleep_sec)
    return n_in_scope


def pull_price_histories(
    cache: Path, *, client: httpx.Client, sleep_sec: float, fidelity_min: int = 1
) -> tuple[int, int]:
    """Fetch CLOB prices-history for every resolved in-scope market's UP token."""
    from backtest.gamma_corpus import iter_cached_rows

    prices_dir = cache / "prices"
    prices_dir.mkdir(parents=True, exist_ok=True)
    n_ok = n_fail = 0
    for row in iter_cached_rows(cache):
        m = parse_updown_market(row)
        if m is None or m.outcome_up is None:
            continue
        out = prices_dir / f"{m.clob_token_up}.json"
        if out.is_file():
            continue
        params = {
            "market": m.clob_token_up,
            "startTs": int(m.open_ts) - 60,
            "endTs": int(m.close_ts) + 60,
            "fidelity": fidelity_min,
        }
        try:
            r = client.get(CLOB_PRICES, params=params)
            r.raise_for_status()
            out.write_text(r.text)
            n_ok += 1
        except httpx.HTTPError as exc:
            n_fail += 1
            logger.warning("prices-history failed for %s: %s", m.slug, exc)
        time.sleep(sleep_sec)
    return n_ok, n_fail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    ap.add_argument("--max-markets", type=int, default=2000)
    ap.add_argument("--max-pages", type=int, default=400)
    ap.add_argument("--with-prices", action="store_true", default=True)
    ap.add_argument("--no-prices", dest="with_prices", action="store_false")
    ap.add_argument("--sleep", type=float, default=0.25, help="delay between requests")
    ap.add_argument("--fidelity", type=int, default=1, help="price history fidelity (minutes)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cache = Path(args.cache_dir)
    started = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=30.0, headers={"User-Agent": "hermes-corpus-pull/1.0"}) as client:
        n_in_scope = pull_market_pages(
            cache,
            max_markets=args.max_markets,
            max_pages=args.max_pages,
            client=client,
            sleep_sec=args.sleep,
        )
        n_prices_ok = n_prices_fail = 0
        if args.with_prices:
            n_prices_ok, n_prices_fail = pull_price_histories(
                cache, client=client, sleep_sec=args.sleep, fidelity_min=args.fidelity
            )

    manifest = {
        "pulled_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "params": vars(args),
        "n_in_scope_markets": n_in_scope,
        "n_price_files_fetched": n_prices_ok,
        "n_price_fetch_failures": n_prices_fail,
        "sources": {"markets": GAMMA_MARKETS, "prices": CLOB_PRICES},
    }
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "manifest.json").write_text(json.dumps(manifest, indent=2))
    logger.info("manifest: %s", json.dumps(manifest, indent=2))

    from backtest.gamma_corpus import load_corpus

    corpus = load_corpus(cache_dir=cache)
    print(corpus.summary.text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
