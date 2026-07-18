"""Historical / CSV loader for backtests.

Supports:
  - real corpus via backtest.gamma_corpus (preferred; cache-first)
  - Gamma API / cache (best-effort, snapshot-level)
  - CSV stub: market_id, decision_time, p, q, resolution_outcome [, true_q, category, ...]

The old "example historical CSV" writer fabricated q = true_q + noise —
the exact circular pattern the honest harness forbids — and was removed.
Nothing in this module may invent a model q from a resolution outcome.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from models.market import DecisionPoint, MarketSnapshot

logger = logging.getLogger(__name__)

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CACHE_DIR = Path("data/cache")


def _parse_prices(raw: Any) -> tuple[float, float]:
    if raw is None:
        return 0.5, 0.5
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return 0.5, 0.5
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            return float(raw[0]), float(raw[1])
        except (TypeError, ValueError):
            return 0.5, 0.5
    return 0.5, 0.5


def _cache_path(tag: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"gamma_{tag}.json"


def fetch_gamma_markets(
    *,
    limit: int = 100,
    closed: bool = True,
    tag: str = "resolved",
    timeout: float = 20.0,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    path = _cache_path(tag)
    if use_cache and path.is_file():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    params = {"limit": limit, "closed": str(closed).lower(), "active": "false"}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(GAMMA_MARKETS, params=params)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                data = data.get("markets") or data.get("data") or []
            path.write_text(json.dumps(data[: limit * 2]))
            return list(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gamma fetch failed (%s); using cache/empty", exc)
        if path.is_file():
            return json.loads(path.read_text())
        return []


def gamma_to_snapshots(rows: list[dict[str, Any]], *, category: str = "crypto") -> list[MarketSnapshot]:
    out: list[MarketSnapshot] = []
    for i, row in enumerate(rows):
        yes_p, _ = _parse_prices(row.get("outcomePrices"))
        try:
            mid = float(row.get("lastTradePrice") or yes_p)
        except (TypeError, ValueError):
            mid = yes_p
        resolved_yes: Optional[bool] = None
        if mid >= 0.95:
            resolved_yes = True
        elif mid <= 0.05:
            resolved_yes = False
        # Honesty: no model ran at this timestamp, so there is no model q.
        # q := p is an explicit placeholder (flagged in meta); the old code
        # fabricated q = 0.88/0.12 FROM the outcome, which is peeking.
        q = float(mid)
        slug = str(row.get("slug") or row.get("conditionId") or f"hist_{i}")
        out.append(
            MarketSnapshot(
                market_id=str(row.get("id") or row.get("conditionId") or slug),
                slug=slug,
                question=str(row.get("question") or "")[:200],
                category=category,
                timeframe="1h",
                p=float(min(0.98, max(0.02, mid if 0.05 < mid < 0.95 else yes_p))),
                q=float(min(0.98, max(0.02, q))),
                liquidity_usd=float(row.get("liquidityNum") or row.get("liquidity") or 1000.0),
                volume_24h=float(row.get("volume24hr") or row.get("volume") or 0.0),
                seconds_to_resolution=0.0,
                true_q=1.0 if resolved_yes else (0.0 if resolved_yes is False else None),
                resolved_yes=resolved_yes,
                meta={"source": "gamma", "q_source": "market_placeholder_no_model"},
                as_of=datetime.now(timezone.utc),
            )
        )
    return out


def load_historical(*, limit: int = 200, use_cache: bool = True) -> list[MarketSnapshot]:
    rows = fetch_gamma_markets(limit=limit, closed=True, use_cache=use_cache)
    return [m for m in gamma_to_snapshots(rows) if m.resolved_yes is not None]


def load_decisions_from_csv(path: Path | str) -> list[DecisionPoint]:
    """CSV columns: market_id, decision_time, p, q, resolution_outcome [, true_q, ...]."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    out: list[DecisionPoint] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            outcome = int(float(row["resolution_outcome"]))
            true_q = float(row["true_q"]) if row.get("true_q") not in (None, "") else (
                0.85 if outcome else 0.15
            )
            t = float(row.get("decision_time") or i)
            dtr = float(row.get("days_to_resolution") or 14)
            mid = str(row["market_id"])
            out.append(
                DecisionPoint(
                    market_id=mid,
                    decision_id=f"{mid}_csv{i}",
                    decision_time=t,
                    lifetime_frac=0.6,
                    category=str(row.get("category") or "crypto"),
                    days_to_resolution=dtr,
                    p=float(row["p"]),
                    q=float(row["q"]),
                    liquidity_usd=float(row.get("liquidity_usd") or 5000),
                    volume_24h=float(row.get("volume_24h") or 8000),
                    true_q=true_q,
                    resolved_yes=bool(outcome),
                    resolution_time=t + dtr,
                    meta={"source": "csv"},
                )
            )
    return out


def load_historical_decisions(
    csv_path: Optional[Path | str] = None,
) -> list[DecisionPoint]:
    """Prefer explicit CSV, then the real gamma corpus cache, then snapshots."""
    if csv_path:
        return load_decisions_from_csv(csv_path)
    from backtest.gamma_corpus import DEFAULT_CACHE_DIR, load_corpus

    if (Path(DEFAULT_CACHE_DIR) / "pages").is_dir():
        corpus = load_corpus()
        if corpus.decisions:
            return corpus.decisions
    snaps = load_historical(limit=200)
    decisions: list[DecisionPoint] = []
    for i, m in enumerate(snaps):
        if m.resolved_yes is None:
            continue
        decisions.append(
            DecisionPoint(
                market_id=m.market_id,
                decision_id=f"{m.market_id}_g0",
                decision_time=float(i),
                lifetime_frac=0.6,
                category=m.category,
                days_to_resolution=14.0,
                p=m.p,
                q=m.q,
                liquidity_usd=m.liquidity_usd,
                volume_24h=m.volume_24h,
                true_q=float(m.true_q if m.true_q is not None else m.q),
                resolved_yes=bool(m.resolved_yes),
                resolution_time=float(i) + 14.0,
                meta={"source": "gamma"},
            )
        )
    return decisions
