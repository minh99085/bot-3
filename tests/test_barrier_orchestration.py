"""compute_cex_implied_up must use the strike-aware barrier q as PRIMARY when
the window-open strike is available, and fall back to the ensemble otherwise."""

from __future__ import annotations

import hermes.mispricing as mp


def _patch_history(monkeypatch, prices):
    times = [float(i) for i in range(len(prices))]
    monkeypatch.setattr(
        mp, "get_asset_price_history", lambda asset, max_points=240: (times, list(prices))
    )


def test_barrier_is_primary_q_when_strike_present(monkeypatch):
    # Spot 0.2% above the window-open strike → barrier q should be clearly
    # bullish and come from the barrier, not the momentum ensemble.
    prices = [64000.0 + 5 * i for i in range(30)]  # gently rising history
    _patch_history(monkeypatch, prices)
    q, features, meta = mp.compute_cex_implied_up(
        momentum=0.2,
        timeframe="5m",
        pm_implied_up=0.60,
        spot=64128.0,
        asset="ETH",  # non-BTC skips the top-of-book path
        seconds_to_resolution=150,
        strike=64000.0,
    )
    assert meta["model_q_source"] == "barrier_cex_open"
    assert q > 0.6  # bullish: spot above open
    assert features.get("barrier_q") is not None
    assert features.get("barrier_sigma_ann", 0) > 0


def test_falls_back_to_ensemble_without_strike(monkeypatch):
    prices = [64000.0 + 5 * i for i in range(30)]
    _patch_history(monkeypatch, prices)
    q, features, meta = mp.compute_cex_implied_up(
        momentum=0.2,
        timeframe="5m",
        pm_implied_up=0.60,
        spot=64128.0,
        asset="ETH",
        seconds_to_resolution=150,
        strike=None,
    )
    assert meta["model_q_source"] in ("advanced_ensemble", "momentum_fallback")


def test_barrier_agrees_with_efficient_market_gives_small_edge(monkeypatch):
    """The money property: fresh-spot barrier ≈ an efficient market that
    already repriced → the edge (|q - p|) is small, so no over-trading."""
    prices = [64000.0 + 5 * i for i in range(30)]
    _patch_history(monkeypatch, prices)
    spot, strike, tau = 64128.0, 64000.0, 150
    # Market that priced the same barrier with realistic vol
    from strategy.advanced_signals import barrier_implied_up

    pm = barrier_implied_up(spot, strike, 1.0, tau)
    q, _, meta = mp.compute_cex_implied_up(
        momentum=0.2, timeframe="5m", pm_implied_up=pm, spot=spot,
        asset="ETH", seconds_to_resolution=tau, strike=strike,
    )
    assert meta["model_q_source"] == "barrier_cex_open"
    # q uses realized σ from the (very smooth) synthetic history, so it won't
    # match pm exactly, but both price the same contract → not a huge edge.
    assert abs(q - pm) < 0.5


def test_resolve_open_strike_uses_price_at_timestamp(monkeypatch):
    import connectors.cex_realtime as cx

    monkeypatch.setattr(cx, "price_at_timestamp", lambda asset, ts: 63950.0)
    mp._OPEN_STRIKE_CACHE.clear()
    px = mp.resolve_open_strike("BTC", 1784420700)
    assert px == 63950.0
    # cached on second call (no second lookup needed)
    monkeypatch.setattr(cx, "price_at_timestamp", lambda asset, ts: 0.0)
    assert mp.resolve_open_strike("BTC", 1784420700) == 63950.0
