"""Universal 5m TV feed — ALL lanes + BTC/ETH symbols.

Bot 3 TV alerts are 5m bar-close for both symbols (INDEX *USD + *USDT).
RSI divergence/band are optional/off; price-pattern from bar-close history
drives confirm/fade + sizing when RSI is disabled.
"""

from __future__ import annotations

from typing import Optional

from engine.pulse.tv_rsi_overlay import (
    latest_rsi_overlay,
    resolve_rsi_overlay_from_intake,
    rsi_overlay_decision,
    size_mult_for_rsi_overlay,
)


# Bot 3 chart symbols per lane: INDEX *USD (15m/Chainlink) + *USDT (1h/Binance).
BTC_SYMBOLS = ("BTCUSD", "INDEX:BTCUSD", "BTC", "BTCUSDT", "BINANCE:BTCUSDT")
ETH_SYMBOLS = ("ETHUSD", "INDEX:ETHUSD", "ETH", "ETHUSDT", "BINANCE:ETHUSDT")


def _asset_from_window(window) -> str:
    slug = str(getattr(window, "series_slug", "") or "").lower()
    label = str(getattr(window, "series_label", "") or "").lower()
    if "eth" in slug or "eth" in label or "ethereum" in slug:
        return "eth"
    return "btc"


def _lane_from_window(window) -> str:
    ws = int(getattr(window, "window_seconds", 900) or 900)
    if ws >= 3600:
        return "1h"
    if ws >= 600:
        return "15m"
    return "5m"


def _chart_symbol_for(asset: str, lane: str) -> str:
    a = str(asset or "btc").lower()
    if lane == "1h":
        return "ETHUSDT" if a == "eth" else "BTCUSDT"
    return "ETHUSD" if a == "eth" else "BTCUSD"


def _resolve_for_cands(intake, candidates: tuple, *, now: float,
                      max_age_s: float) -> Optional[dict]:
    if intake is None:
        return None
    for cand in candidates:
        try:
            rows = list(intake.rsi_div_history_for_symbol(cand) or [])
        except Exception:  # noqa: BLE001
            rows = []
        ov = latest_rsi_overlay(rows, now=float(now), max_age_s=float(max_age_s))
        if ov:
            return {**ov, "resolved_symbol": cand}
    for cand in candidates[:1]:
        ov = resolve_rsi_overlay_from_intake(
            intake, cand, now=float(now), max_age_s=float(max_age_s))
        if ov:
            return ov
    return None


def cross_asset_agreement(btc: Optional[dict], eth: Optional[dict]) -> dict:
    """Score BTC vs ETH lean agreement (RSI overlay or bar-close trade_lean)."""
    b_lean = str((btc or {}).get("lean") or "").lower() or None
    e_lean = str((eth or {}).get("lean") or "").lower() or None
    if not b_lean and not e_lean:
        return {"status": "silent", "lean": None, "agreement": None, "score": 0.5}
    if b_lean and e_lean:
        if b_lean == e_lean:
            return {"status": "agree", "lean": b_lean, "agreement": True, "score": 1.0}
        return {"status": "conflict", "lean": None, "agreement": False, "score": 0.2}
    only = b_lean or e_lean
    return {"status": "single_asset", "lean": only, "agreement": None, "score": 0.65}


def _price_pattern_block(
    intake,
    *,
    asset: str,
    lane: str,
    short_n: int = 8,
    regime_n: int = 20,
    allow_rsi_div_fallback: bool = False,
) -> dict:
    """Dual-horizon price pattern from TV history for this lane/asset."""
    empty = {
        "enabled": True,
        "path_source": "empty",
        "trade_lean": None,
        "alignment": "none",
        "confidence": "none",
        "short_pattern": None,
        "regime_pattern": None,
        "short_n": 0,
        "regime_n": 0,
    }
    if intake is None:
        return empty
    try:
        from engine.pulse.tv_15m_price_path import (
            compact_path_for_plot,
            dual_horizon_price_path,
            resolve_price_path_from_intake,
            trade_lean_from_path,
        )
        requested = _chart_symbol_for(asset, lane)
        sn = max(6, int(12 if lane == "1h" else short_n))
        rn = max(sn, int(regime_n))
        sym, alerts, source = resolve_price_path_from_intake(
            intake, requested, strict_lane=True,
            allow_rsi_div_fallback=bool(allow_rsi_div_fallback))
        if not alerts:
            return {**empty, "symbol": sym, "requested_symbol": requested}
        dual = dual_horizon_price_path(
            alerts, regime_n=rn, short_n=sn, path_source=source)
        lean = trade_lean_from_path(dual)
        return {
            "enabled": True,
            "path_source": source,
            "symbol": sym,
            "requested_symbol": requested,
            "lane": lane,
            "asset": asset,
            "trade_lean": lean.get("trade_lean"),
            "alignment": lean.get("alignment") or "none",
            "confidence": lean.get("confidence") or "none",
            "short_pattern": lean.get("short_pattern"),
            "regime_pattern": lean.get("regime_pattern"),
            "short_n": lean.get("short_n") or 0,
            "regime_n": lean.get("regime_n") or 0,
            "price_pattern": compact_path_for_plot(dual),
            "dual": {
                "alignment": dual.get("alignment"),
                "trade_lean": dual.get("trade_lean"),
                "confidence": dual.get("confidence"),
                "path_source": dual.get("path_source"),
            },
        }
    except Exception:  # noqa: BLE001
        return empty


def universal_tv_snapshot(
    intake,
    *,
    window=None,
    asset: Optional[str] = None,
    now: float,
    max_age_s: float = 2700.0,
    proposed_side: Optional[str] = None,
    aligned_mult: float = 1.15,
    opposed_mult: float = 0.45,
    use_rsi: bool = True,
    allow_rsi_div_fallback: bool = False,
) -> dict:
    """5m bar-close price-pattern (+ optional RSI) for all lanes.

    When ``use_rsi=False`` (Bot-3 default), lean/confirm/fade come from
    bar-close dual-horizon patterns only.
    """
    asset_l = (asset or (_asset_from_window(window) if window is not None else "btc")).lower()
    lane = _lane_from_window(window) if window is not None else "15m"

    price_pat = _price_pattern_block(
        intake, asset=asset_l, lane=lane,
        allow_rsi_div_fallback=bool(allow_rsi_div_fallback))
    # Cross-asset from the other asset's bar-close pattern (always useful)
    other = "eth" if asset_l == "btc" else "btc"
    other_pat = _price_pattern_block(
        intake, asset=other, lane=lane,
        allow_rsi_div_fallback=bool(allow_rsi_div_fallback))

    if use_rsi:
        btc = _resolve_for_cands(intake, BTC_SYMBOLS, now=now, max_age_s=max_age_s)
        eth = _resolve_for_cands(intake, ETH_SYMBOLS, now=now, max_age_s=max_age_s)
        x = cross_asset_agreement(btc, eth)
        focus = btc if asset_l == "btc" else eth
        focus_lean = str((focus or {}).get("lean") or "").lower() or None
        effective_lean = focus_lean or x.get("lean")
        source = "tv_5m_rsi_divergence_universal"
        strength = float((focus or {}).get("strength") or 0.75)
    else:
        # RSI off: bar-close trade_lean is the TV signal for all lanes
        btc_pat = price_pat if asset_l == "btc" else other_pat
        eth_pat = price_pat if asset_l == "eth" else other_pat
        btc = {
            "lean": btc_pat.get("trade_lean"),
            "strength": 0.75,
            "resolved_symbol": btc_pat.get("symbol"),
            "source": "bar_close_5m",
        }
        eth = {
            "lean": eth_pat.get("trade_lean"),
            "strength": 0.75,
            "resolved_symbol": eth_pat.get("symbol"),
            "source": "bar_close_5m",
        }
        x = cross_asset_agreement(btc, eth)
        focus = btc if asset_l == "btc" else eth
        effective_lean = str(price_pat.get("trade_lean") or "").lower() or x.get("lean")
        source = "tv_5m_bar_close_universal"
        strength = 0.75

    decision = rsi_overlay_decision(
        side=proposed_side,
        overlay={"lean": effective_lean} if effective_lean else None,
    )
    size_mult = size_mult_for_rsi_overlay(
        side=proposed_side,
        overlay={"lean": effective_lean} if effective_lean else None,
        aligned_mult=aligned_mult,
        opposed_mult=opposed_mult,
    )
    # Soft alignment haircut from dual-horizon when bar-close path is divergent
    if not use_rsi and str(price_pat.get("alignment") or "") == "divergent":
        size_mult *= 0.85
    if x.get("status") == "conflict":
        size_mult *= 0.75
    elif x.get("status") == "agree" and decision.get("decision") == "confirm":
        size_mult *= 1.08

    return {
        "enabled": True,
        "source": source,
        "use_rsi": bool(use_rsi),
        "lane": lane,
        "asset": asset_l,
        "btc": btc,
        "eth": eth,
        "cross_asset": x,
        "focus": {**(focus or {}), "strength": strength},
        "effective_lean": effective_lean,
        "decision": decision,
        "size_mult": round(float(size_mult), 4),
        "price_pattern": price_pat,
        "note": (
            "Same 5m bar-close alerts feed ALL lanes (5m/15m/1h) and both assets "
            "via price-pattern lean. RSI overlay %s. Never overrides Chainlink "
            "price_action_trend." % ("ON" if use_rsi else "OFF")
        ),
    }
