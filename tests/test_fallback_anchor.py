"""The momentum fallback must anchor to the market, not float free.

When the ensemble lacks history/book it falls back to `momentum_to_q`. That
map takes SATURATED momentum (which a sub-0.15% move already produces) to
q≈0.85 with ZERO market anchoring — so against a coinflip market (p≈0.51) it
manufactured a 0.34 edge from noise (the logged SOL `advanced_fallback_smoothed`
trade, enhanced_edge=0.36). A fallback fires precisely because the model has
little real signal, so its q must be pulled toward the market, not asserted
with full confidence.
"""

from __future__ import annotations

from strategy.advanced_signals import ensemble_cex_implied_up, momentum_to_q


def _fallback_result(momentum: float, p_mkt: float):
    # Thin history (<5 points) forces the insufficient_history fallback.
    return ensemble_cex_implied_up(
        prices=[100.0, 100.1],
        times=[0.0, 1.0],
        momentum=momentum,
        timeframe="5m",
        pm_implied_up=p_mkt,
        spot=100.0,
    )


def test_saturated_momentum_fallback_edge_is_bounded():
    res = _fallback_result(momentum=1.0, p_mkt=0.51)
    assert res.used_fallback is True
    # Must NOT claim a huge edge from a coinflip market on saturated momentum
    assert abs(res.q - 0.51) <= 0.12, f"fallback edge {abs(res.q - 0.51):.3f} too large"


def test_fallback_pulls_toward_market_not_to_0_85():
    # Bare momentum_to_q(1.0) = 0.85; the anchored fallback must sit well below
    assert momentum_to_q(1.0) >= 0.84
    res = _fallback_result(momentum=1.0, p_mkt=0.50)
    assert res.q < 0.75


def test_fallback_still_tilts_in_signal_direction():
    up = _fallback_result(momentum=1.0, p_mkt=0.50).q
    down = _fallback_result(momentum=-1.0, p_mkt=0.50).q
    # Directional information preserved, just damped
    assert up > 0.50 > down


def test_fallback_neutral_when_market_neutral_and_no_momentum():
    res = _fallback_result(momentum=0.0, p_mkt=0.50)
    assert abs(res.q - 0.50) <= 0.02
