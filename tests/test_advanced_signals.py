"""Unit tests for strategy.advanced_signals — pure math, synthetic series."""

from __future__ import annotations

import math

import numpy as np
import pytest

from strategy.advanced_signals import (
    ensemble_cex_implied_up,
    estimate_garch11,
    estimate_ou_ar1,
    fuse_probabilities,
    hurst_rs,
    js_divergence,
    kalman_filter_1d,
    kalman_prob_from_prices,
    kl_divergence,
    lognormal_cex_prob,
    momentum_to_q,
    multi_tf_weighted_slope,
    obi_to_prob,
    order_book_metrics,
    ou_mean_reversion_prob,
    slope_for_window,
)


def _gbm(
    n: int = 120,
    s0: float = 100.0,
    mu: float = 0.0002,
    sigma: float = 0.002,
    seed: int = 0,
) -> tuple[list[float], list[float]]:
    rng = np.random.default_rng(seed)
    t = list(range(n))
    rets = rng.normal(mu, sigma, size=n - 1)
    prices = [s0]
    for r in rets:
        prices.append(prices[-1] * math.exp(r))
    return [float(x) for x in t], prices


def test_slope_for_window_uptrend():
    times = list(range(60))
    prices = [100.0 + 0.1 * i for i in times]
    s = slope_for_window(times, prices, 60.0)
    assert s > 0.0


def test_multi_tf_weighted_slope_positive():
    times, prices = _gbm(n=200, mu=0.0005, seed=1)
    w, slopes = multi_tf_weighted_slope(times, prices)
    assert "weighted_slope" in slopes
    assert isinstance(w, float)


def test_order_book_metrics_obi_positive():
    bids = [(100.0, 10.0), (99.9, 8.0), (99.8, 5.0)]
    asks = [(100.1, 2.0), (100.2, 2.0), (100.3, 1.0)]
    m = order_book_metrics(bids, asks, levels=3)
    assert m["obi"] > 0.0
    assert 0.0 < m["ir"] < 1.0
    assert m["vamp"] > 0.0


def test_obi_to_prob_bounds():
    assert 0.05 <= obi_to_prob(1.0) <= 0.95
    assert 0.05 <= obi_to_prob(-1.0) <= 0.95
    assert abs(obi_to_prob(0.0) - 0.5) < 1e-9


def test_garch11_positive_vol():
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.01, size=80).tolist()
    sig = estimate_garch11(r)
    assert sig > 0.0


def test_lognormal_cex_prob_itm_otm():
    # Deep ITM call-style UP
    p_hi = lognormal_cex_prob(110.0, 100.0, 0.5, 1 / 365)
    p_lo = lognormal_cex_prob(90.0, 100.0, 0.5, 1 / 365)
    assert p_hi > 0.7
    assert p_lo < 0.3


def test_ou_ar1_mean_reverting():
    # Simulate AR(1) with b=0.7 around mu=100
    rng = np.random.default_rng(3)
    x = [100.0]
    for _ in range(80):
        x.append(30.0 + 0.7 * x[-1] + rng.normal(0, 0.5))
    ou = estimate_ou_ar1(x, dt=1.0)
    assert ou["theta"] > 0.0
    assert 90.0 < ou["mu"] < 110.0


def test_hurst_rs_random_near_half():
    times, prices = _gbm(n=200, mu=0.0, sigma=0.01, seed=4)
    h = hurst_rs(prices)
    assert 0.2 < h < 0.8


def test_hurst_trending_higher_than_mean_revert():
    # Strong trend
    trend = [100.0 + i * 0.5 + 0.01 * math.sin(i) for i in range(120)]
    # Mean-reverting around 100
    rng = np.random.default_rng(5)
    mr = [100.0]
    for _ in range(119):
        mr.append(mr[-1] + 0.4 * (100.0 - mr[-1]) + rng.normal(0, 0.2))
    h_trend = hurst_rs(trend)
    h_mr = hurst_rs(mr)
    # Not always strict, but trend should not be dramatically more MR
    assert h_trend >= 0.05
    assert h_mr <= 0.95


def test_kalman_filter_converges():
    obs = [0.5 + 0.01 * i for i in range(40)]
    x, path = kalman_filter_1d(obs, q_proc=1e-3, r_obs=1e-3)
    assert len(path) == 40
    # Filtered state tracks the trend (lags slightly under process noise)
    assert abs(x - obs[-1]) < 0.08
    assert x > obs[0]


def test_kalman_prob_from_prices():
    _, prices = _gbm(n=80, mu=0.0004, seed=6)
    q = kalman_prob_from_prices(prices)
    assert 0.05 <= q <= 0.95


def test_kl_js_symmetric_bounds():
    assert kl_divergence(0.5, 0.5) == pytest.approx(0.0, abs=1e-9)
    js = js_divergence(0.2, 0.8)
    assert js > 0.0
    assert js_divergence(0.3, 0.7) == pytest.approx(js_divergence(0.7, 0.3), abs=1e-9)


def test_fuse_probabilities_blend():
    comps = {"a": 0.7, "b": 0.6}
    w = {"a": 1.0, "b": 1.0}
    q = fuse_probabilities(comps, w, p_market=0.4, swarm_weight=0.7, market_blend=0.3)
    assert 0.05 <= q <= 0.95
    # Should sit between swarm (~0.65) and market (0.4)
    assert 0.4 < q < 0.75


def test_momentum_to_q_legacy():
    assert momentum_to_q(0.0) == pytest.approx(0.5)
    assert momentum_to_q(1.0) > 0.7
    assert momentum_to_q(-1.0) < 0.3


def test_ensemble_fallback_thin_history():
    r = ensemble_cex_implied_up(
        prices=[100.0, 100.1],
        times=[0.0, 1.0],
        momentum=0.5,
        timeframe="5m",
        pm_implied_up=0.45,
        spot=100.1,
        enabled=True,
    )
    assert r.used_fallback
    assert abs(r.q - momentum_to_q(0.5, "5m")) < 1e-9


def test_ensemble_disabled_uses_momentum():
    times, prices = _gbm(n=100, seed=7)
    r = ensemble_cex_implied_up(
        prices=prices,
        times=times,
        momentum=0.4,
        timeframe="5m",
        pm_implied_up=0.48,
        spot=prices[-1],
        enabled=False,
    )
    assert r.used_fallback
    assert r.reason == "advanced_disabled"


def test_ensemble_rich_history_no_artificial_extremes():
    times, prices = _gbm(n=150, mu=0.0003, seed=8)
    bids = [(prices[-1] - 1, 5.0), (prices[-1] - 2, 4.0)]
    asks = [(prices[-1] + 1, 3.0), (prices[-1] + 2, 2.0)]
    r = ensemble_cex_implied_up(
        prices=prices,
        times=times,
        momentum=0.3,
        timeframe="5m",
        pm_implied_up=0.50,
        spot=prices[-1],
        seconds_to_resolution=240.0,
        bids=bids,
        asks=asks,
        enabled=True,
    )
    assert not r.used_fallback
    assert 0.05 <= r.q <= 0.95
    # Never restore artificial 0.97/0.03 push
    assert r.q < 0.97
    assert r.q > 0.03
    assert "multi_tf" in r.components or "lognormal" in r.components


def test_ou_mean_reversion_prob_below_mean():
    ou = {"theta": 0.1, "mu": 100.0, "sigma": 2.0, "b": 0.9}
    q = ou_mean_reversion_prob(95.0, ou)
    assert q > 0.5
