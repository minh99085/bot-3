"""Discovery — find high-quality trading opportunities autonomously.

Move 1 of the loop. Reads SKILL.md + ALPHA_RESEARCH_SKILL.md + STATE.md,
pulls Polymarket markets via connector, scores candidates by regime,
liquidity, spread, and historical edge buckets. Does NOT generate trades —
that is signal_generator's job.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from hermes.decorators import loop
from hermes.models import (
    EdgeBucket,
    EntryMode,
    MarketCandidate,
    Regime,
)
from hermes.state_io import (
    ensure_dirs,
    parse_state_fields,
    read_alpha_skill,
    read_lessons_md,
    read_skill,
    read_state_md,
    write_handoff,
)

logger = logging.getLogger(__name__)

# Hard gates from Hermes weakness post-mortem
MIN_LIQUIDITY_USD = 5_000.0
MAX_SPREAD_BPS = 250.0
MIN_VOLUME_24H = 1_000.0
GATED_MODES = {EntryMode.OSMANI_LANE}  # kill/gate until WR>65% + +EV backtest


def _hour_utc() -> int:
    return datetime.now(timezone.utc).hour


def detect_regime(
    yes_price: float,
    volume_24h: float,
    spread_bps: float,
    price_change_1h: float = 0.0,
) -> Regime:
    """Lightweight regime detector — replace with richer model later."""
    if spread_bps > 400:
        return Regime.HIGH_VOL
    if volume_24h < 500:
        return Regime.LOW_VOL
    if abs(price_change_1h) >= 0.08:
        return Regime.TRENDING_UP if price_change_1h > 0 else Regime.TRENDING_DOWN
    if abs(price_change_1h) <= 0.015 and 0.25 <= yes_price <= 0.75:
        return Regime.MEAN_REVERT
    if volume_24h > 50_000 and spread_bps < 100:
        return Regime.TRENDING_UP if price_change_1h >= 0 else Regime.TRENDING_DOWN
    # Prefer a usable default over UNKNOWN so verifier regime filter can fire
    if 0.15 <= yes_price <= 0.85 and volume_24h >= 1_000:
        return Regime.MEAN_REVERT
    if volume_24h >= 1_000:
        return Regime.LOW_VOL
    return Regime.UNKNOWN


def load_edge_buckets_from_alpha() -> list[EdgeBucket]:
    """Seed + parse AVOID / EXPLOIT hints from ALPHA_RESEARCH_SKILL.md."""
    from hermes.models import ConfidenceTier

    text = read_alpha_skill()
    buckets = [
        EdgeBucket(
            regime=Regime.HIGH_VOL,
            hourly_bucket=0,
            entry_mode=EntryMode.OSMANI_LANE,
            confidence_tier=ConfidenceTier.C,
            sample_n=12,
            win_rate=0.42,
            avg_edge=-0.03,
            profit_factor=0.7,
            avoid=True,
            notes="GATED: osmani_lane unproven — need WR>65% + positive EV backtest",
        ),
        EdgeBucket(
            regime=Regime.MEAN_REVERT,
            hourly_bucket=14,
            entry_mode=EntryMode.MEAN_REVERSION,
            confidence_tier=ConfidenceTier.A,
            direction_bias="DOWN",
            sample_n=48,
            win_rate=0.78,
            avg_edge=0.09,
            profit_factor=1.9,
            exploit=True,
            notes="DOWN-biased mean-revert mid-day bucket",
        ),
        EdgeBucket(
            regime=Regime.TRENDING_DOWN,
            hourly_bucket=20,
            entry_mode=EntryMode.MOMENTUM,
            confidence_tier=ConfidenceTier.B,
            direction_bias="DOWN",
            sample_n=35,
            win_rate=0.71,
            avg_edge=0.07,
            profit_factor=1.55,
            exploit=True,
            notes="evening DOWN momentum",
        ),
    ]
    lessons = read_lessons_md().lower()
    if "osmani" in lessons and "avoid" in lessons:
        for b in buckets:
            if b.entry_mode == EntryMode.OSMANI_LANE:
                b.avoid = True
    # Future: NLP parse of EXPLOIT/AVOID tables from `text`
    _ = text
    return buckets


def score_candidate(c: MarketCandidate, buckets: list[EdgeBucket]) -> float:
    """Higher is better. Used to rank discovery output."""
    score = 0.0
    if c.liquidity >= MIN_LIQUIDITY_USD:
        score += 0.25
    if c.spread_bps <= MAX_SPREAD_BPS:
        score += 0.20
    if c.volume_24h >= MIN_VOLUME_24H:
        score += 0.15
    # Prefer mid-priced markets where edge is measurable
    mid = min(c.yes_price, c.no_price)
    if 0.15 <= mid <= 0.45:
        score += 0.15
    # Exploit bucket bonus
    for b in buckets:
        if b.exploit and b.regime == c.regime and (
            b.hourly_bucket == c.hourly_bucket or b.hourly_bucket in (c.hourly_bucket,)
        ):
            score += 0.25 * b.win_rate
    # Penalize unknown regime
    if c.regime == Regime.UNKNOWN:
        score -= 0.10
    return max(0.0, min(1.0, score))


def filter_candidates(
    raw: list[MarketCandidate],
    buckets: list[EdgeBucket],
    *,
    min_score: float = 0.35,
    limit: int = 25,
) -> list[MarketCandidate]:
    scored: list[tuple[float, MarketCandidate]] = []
    for c in raw:
        if c.liquidity < MIN_LIQUIDITY_USD:
            continue
        if c.spread_bps > MAX_SPREAD_BPS:
            continue
        if c.volume_24h < MIN_VOLUME_24H:
            continue
        s = score_candidate(c, buckets)
        if s >= min_score:
            scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def discover_from_connector(limit: int = 50) -> list[MarketCandidate]:
    """Pull markets from Polymarket (prefer crypto up/down) + enrich via Chainlink."""
    import os

    if os.environ.get("HERMES_FORCE_SYNTHETIC", "0") == "1":
        return _synthetic_candidates()
    try:
        from connectors.hybrid_data import HybridDataService
        from connectors.polymarket import PolymarketClient

        client = PolymarketClient()
        try:
            raw = client.list_crypto_updown_markets(limit=limit)
        except Exception:
            raw = client.list_candidate_markets(limit=limit)
        hybrid = HybridDataService(polymarket=client)
        return [hybrid.apply_to_candidate(c) for c in raw]
    except Exception as exc:  # noqa: BLE001
        logger.warning("polymarket/hybrid unavailable (%s); using synthetic set", exc)
        return _synthetic_candidates()


def _synthetic_candidates() -> list[MarketCandidate]:
    """Deterministic paper candidates: BTC/ETH 5m/15m + EXPLOIT-aligned macros."""
    hour = 14
    samples = [
        (
            "mkt_btc_5m",
            "btc-updown-5m",
            "Bitcoin Up or Down - 5 Minutes",
            0.48,
            0.52,
            45000,
            20000,
            60,
            "5m",
            "BTC",
        ),
        (
            "mkt_eth_15m",
            "eth-updown-15m",
            "Ethereum Up or Down - 15 Minutes",
            0.46,
            0.54,
            28000,
            15000,
            70,
            "15m",
            "ETH",
        ),
        (
            "mkt_btc_100k",
            "will-btc-hit-100k",
            "Will BTC hit $100k this month?",
            0.42,
            0.58,
            12000,
            8000,
            80,
            "1h",
            "BTC",
        ),
        (
            "mkt_fed_cut",
            "fed-rate-cut-july",
            "Will the Fed cut rates in July?",
            0.31,
            0.69,
            25000,
            15000,
            60,
            "1h",
            None,
        ),
        (
            "mkt_eth_etf",
            "eth-etf-inflows",
            "Will ETH ETF see net inflows this week?",
            0.55,
            0.45,
            9000,
            6000,
            90,
            "1h",
            "ETH",
        ),
    ]
    out: list[MarketCandidate] = []
    # Optional live Chainlink enrichment even for synthetics
    oracle_map: dict[str, object] = {}
    try:
        from connectors.chainlink import ChainlinkClient

        cl = ChainlinkClient()
        for a in ("BTC", "ETH"):
            px = cl.get_price(a)
            oracle_map[a] = px.price_usd
            oracle_map[f"{a}_src"] = px.source
    except Exception:  # noqa: BLE001
        pass

    for mid, slug, q, yes, no, vol, liq, spread, tf, asset in samples:
        regime = Regime.MEAN_REVERT
        raw = {
            "timeframe": tf,
            "asset": asset,
            "oracle_alignment": 0.75 if asset else 0.55,
            "oracle_return_proxy": -0.001 if asset else 0.0,
            "oracle_price": oracle_map.get(asset) if asset else None,
            "oracle_source": oracle_map.get(f"{asset}_src") if asset else None,
            "oracle_stale": False,
            "synthetic": True,
        }
        tags = ["synthetic", "paper", f"tf:{tf}"]
        if asset:
            tags.append(asset.lower())
        out.append(
            MarketCandidate(
                market_id=mid,
                slug=slug,
                question=q,
                yes_price=yes,
                no_price=no,
                volume_24h=vol,
                liquidity=liq,
                spread_bps=spread,
                regime=regime,
                hourly_bucket=hour,
                timeframe=tf,
                tags=tags,
                raw=raw,
            )
        )
    return out


@loop(interval="5m", name="discovery")
def discovery_tick(turn_id: Optional[str] = None) -> list[MarketCandidate]:
    """Automation entry: discover → hybrid enrich → handoff for signal gen."""
    ensure_dirs()
    _skill = read_skill()
    _alpha = read_alpha_skill()
    state = parse_state_fields(read_state_md())
    if state.get("loop_paused") or state.get("pause_loop"):
        logger.warning("discovery skipped: loop paused in STATE.md")
        return []

    buckets = load_edge_buckets_from_alpha()
    raw = discover_from_connector()
    hour = _hour_utc()
    for c in raw:
        if c.hourly_bucket is None:
            c.hourly_bucket = hour
        tf = (c.raw or {}).get("timeframe") or c.timeframe or "1h"
        c.timeframe = tf
        if c.regime == Regime.UNKNOWN:
            # Prefer oracle-based regime already set by hybrid; else local
            ret = float((c.raw or {}).get("oracle_return_proxy") or 0.0)
            if (c.raw or {}).get("asset"):
                from connectors.hybrid_data import regime_from_oracle

                c.regime = regime_from_oracle(ret, c.spread_bps, c.yes_price, tf)
            else:
                c.regime = detect_regime(c.yes_price, c.volume_24h, c.spread_bps)

    filtered = filter_candidates(raw, buckets)
    tid = turn_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = write_handoff("discovery", filtered, tid)
    logger.info(
        "discovery: %d raw → %d candidates (handoff %s)",
        len(raw),
        len(filtered),
        path.name,
    )
    return filtered
