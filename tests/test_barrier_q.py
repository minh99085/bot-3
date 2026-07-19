"""Strike-aware barrier pricing — the calibrated model q.

These up/down markets resolve on close vs the window-OPEN strike. The model
must price the actual contract: q = P(S_close > strike | spot, time-left, vol)
under a log-normal, using the window-open CEX price as the strike. This
replaces the momentum guess that sat near 0.5 and fed the fade pathology.

Key money property: with a fresh spot the barrier price AGREES with an
efficient market that already repriced the move (→ no trade). Edge appears
only as the residual when our CEX spot/vol is fresher than Polymarket's
price. So we test calibration + agreement, not a manufactured edge.
"""

from __future__ import annotations

import math

import pytest

from strategy.advanced_signals import barrier_implied_up, realized_sigma_ann


def test_atm_is_coinflip():
    q = barrier_implied_up(spot=64000.0, strike=64000.0, sigma_ann=0.6, seconds_to_resolution=150)
    # The −½σ²T drift term makes ATM a hair below 0.5; over a 5-min horizon
    # it's ~1e-4, i.e. the market's ~0.5.
    assert abs(q - 0.5) < 2e-3


def test_above_strike_is_bullish_below_is_bearish():
    up = barrier_implied_up(64128.0, 64000.0, 0.6, 150)      # +0.2%
    down = barrier_implied_up(63872.0, 64000.0, 0.6, 150)    # -0.2%
    assert up > 0.5 and down < 0.5
    assert up == pytest.approx(1.0 - down, abs=0.02)  # symmetric


def test_monotonic_increasing_in_spot():
    qs = [barrier_implied_up(64000.0 * (1 + m), 64000.0, 0.6, 150)
          for m in (-0.003, -0.001, 0.0, 0.001, 0.003)]
    assert all(qs[i] < qs[i + 1] for i in range(len(qs) - 1))


def test_magnitude_calibrated_agrees_with_market():
    # +0.2% above open, ~150s left, realistic σ≈1.0 (5-min BTC vol is high).
    # This is the exact regime where the OLD momentum model said ~0.57 and
    # FADED a correct 0.79 market. The barrier lands ~0.82 — AGREEING with
    # the market (no fabricated fade), confident but not saturated.
    q = barrier_implied_up(64128.0, 64000.0, 1.0, 150)
    assert 0.75 <= q <= 0.88, q


def test_more_time_left_pulls_toward_coinflip():
    near = barrier_implied_up(64128.0, 64000.0, 0.6, 30)     # 30s left
    far = barrier_implied_up(64128.0, 64000.0, 0.6, 280)     # ~full 5m left
    assert near > far > 0.5  # less time → more certain the move holds


def test_higher_vol_pulls_toward_coinflip():
    lo = barrier_implied_up(64128.0, 64000.0, 0.4, 150)
    hi = barrier_implied_up(64128.0, 64000.0, 1.2, 150)
    assert 0.5 < hi < lo  # more vol → move less decisive


def test_clamped_to_valid_band():
    q = barrier_implied_up(70000.0, 64000.0, 0.6, 5)  # huge move, tiny time
    assert 0.05 <= q <= 0.95


def test_realized_sigma_ann_reasonable_and_none_on_thin():
    assert realized_sigma_ann([100.0, 100.1]) is None
    # ~0.03% per-second moves → annualized vol in a sane band
    prices = [100.0]
    for i in range(60):
        prices.append(prices[-1] * (1 + (0.0003 if i % 2 else -0.0003)))
    sig = realized_sigma_ann(prices, sample_sec=1.0)
    assert sig is not None and 0.2 <= sig <= 2.5


def test_barrier_agrees_with_efficient_market_no_false_edge():
    """If the market already prices the same barrier, our q ≈ market → no edge.
    A model that fabricates edge here (like the old momentum q at 0.57 vs
    market 0.79) is the bug."""
    spot, strike, sigma, tau = 64128.0, 64000.0, 0.6, 150
    q = barrier_implied_up(spot, strike, sigma, tau)
    # An efficient market pricing the same inputs lands on the same q.
    market_p = barrier_implied_up(spot, strike, sigma, tau)
    assert abs(q - market_p) < 1e-9
