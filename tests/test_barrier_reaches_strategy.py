"""The barrier q must survive the trip into the strategy layer.

Regression: compute_cex_implied_up returned the barrier as q, but left
features['advanced_q'] holding the raw ensemble q — and
enhance_from_hermes_mispricing PREFERS advanced_q, clobbering the barrier.
Live ledger proof: VPS trades on commit 6e7f3b4 still logged
q≈0.58 src=advanced_ensemble_smoothed and kept fading 0.79 markets.
"""

from __future__ import annotations

import pytest

import hermes.mispricing as mp
from strategy.enhanced_misprice import enhance_from_hermes_mispricing


def test_compute_features_advanced_q_is_the_barrier(monkeypatch):
    prices = [64000.0 + 4 * i for i in range(40)]
    monkeypatch.setattr(
        mp, "get_asset_price_history",
        lambda asset, max_points=240: ([float(i) for i in range(len(prices))], list(prices)),
    )
    q, features, meta = mp.compute_cex_implied_up(
        momentum=0.5, timeframe="5m", pm_implied_up=0.79,
        spot=64128.0, asset="ETH", seconds_to_resolution=150, strike=64000.0,
    )
    assert meta["model_q_source"] == "barrier_cex_open"
    # The q consumers read from features must BE the returned barrier q
    assert features["advanced_q"] == pytest.approx(q)
    assert features["barrier_q"] == pytest.approx(q)
    # ensemble preserved separately for diagnostics
    assert "ensemble_q" in features


def test_barrier_q_survives_enhance_wrapper(monkeypatch):
    """End-to-end: the strategy's final opp.q must be the barrier, unshrunk."""
    barrier_q = 0.82
    opp = enhance_from_hermes_mispricing(
        market_id="m1",
        slug="btc-updown-5m-1784459700",
        pm_implied_up=0.79,
        cex_implied_up=barrier_q,
        dislocation=0.03,
        mp_conviction=0.9,
        timeframe="5m",
        advanced_features={
            "advanced_q": barrier_q,   # post-fix: carries the barrier
            "barrier_q": barrier_q,
            "barrier_sigma_ann": 1.0,
            "advanced_used_fallback": 0.0,
        },
    )
    # Barrier is already calibrated: NO 0.5-shrink (which widened the fade
    # edge against stretched markets), just clamped.
    assert opp.q == pytest.approx(barrier_q, abs=1e-9)
    assert opp.meta["model_q_source"] == "barrier_cex_open"


def test_non_barrier_path_still_shrinks(monkeypatch):
    """Without a barrier, the ensemble q keeps its light 0.5-shrink."""
    q_raw = 0.70
    opp = enhance_from_hermes_mispricing(
        market_id="m2",
        slug="btc-updown-5m-1784459700",
        pm_implied_up=0.60,
        cex_implied_up=q_raw,
        dislocation=0.05,
        mp_conviction=0.9,
        timeframe="5m",
        advanced_features={"advanced_q": q_raw, "advanced_used_fallback": 0.0},
    )
    assert opp.q == pytest.approx(0.5 + 0.90 * (q_raw - 0.5))
    assert opp.meta["model_q_source"] == "advanced_ensemble_smoothed"
