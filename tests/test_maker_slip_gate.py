"""Maker lanes must be gated on MAKER slip, not the taker VWAP walk.

Regression for the 2026-07-24 finding: the 150bps slippage gate measured taker
slippage for maker lanes, so it rejected every maker entry on thin 15m books
(the two features shipped 2026-07-23 cancelled each other out).
"""

from __future__ import annotations

import pytest

import hermes.pretrade as pt
from hermes.models import ConfidenceTier, Direction, EntryMode, Regime, Signal
from hermes.substrategy import annotate_signal


class _Book:
    def __init__(self, mid, best_ask):
        self.mid = mid
        self.best_ask = best_ask
        self.asks = [type("L", (), {"price": best_ask, "size": 1000.0})()]
        self.bids = []


def _sig():
    return annotate_signal(Signal(
        market_id="mkt_btc", slug="btc-updown-15m-1784601000",
        question="Bitcoin Up or Down", direction=Direction.UP,
        entry_mode=EntryMode.MISPRICING, confidence_tier=ConfidenceTier.A,
        regime=Regime.MEAN_REVERT, conviction=0.8, fair_value=0.90,
        market_price=0.80, expected_edge=0.10, live_ev=0.08, hourly_bucket=14,
        size_usd_suggested=40.0, entry_vwap_target=0.80,
        pre_entry_stability_ok=True, timeframe="15m", oracle_alignment=0.6,
        clob_token_id="tok", meta={"paper": True, "asset": "BTC", "mispricing_active": True},
    ))


def _patch_book(monkeypatch, mid, best_ask):
    import connectors.polymarket as pm

    monkeypatch.setattr(pm.PolymarketClient, "get_orderbook",
                        lambda self, t: _Book(mid, best_ask))
    monkeypatch.setattr(pm.PolymarketClient, "simulate_buy_vwap",
                        lambda self, t, s: (best_ask, (best_ask - mid) / mid * 10_000.0))


def test_taker_slip_measured_as_full_walk(monkeypatch):
    monkeypatch.delenv("HERMES_MAKER_MODE", raising=False)
    _patch_book(monkeypatch, mid=0.78, best_ask=0.80)  # ~256bps taker
    _ev, slip, note = pt._recalc_live_ev(_sig())
    assert slip == pytest.approx((0.80 - 0.78) / 0.78 * 10_000, rel=1e-3)
    assert "book_slip" in note


def test_maker_slip_is_a_fraction_of_taker(monkeypatch):
    monkeypatch.setenv("HERMES_MAKER_MODE", "1")
    _patch_book(monkeypatch, mid=0.78, best_ask=0.80)
    _ev, slip, note = pt._recalc_live_ev(_sig())
    # maker concedes 25% of the half-spread: (0.78 + 0.25*0.02 - 0.78)/0.78
    assert slip == pytest.approx(0.25 * 0.02 / 0.78 * 10_000, rel=1e-3)
    assert "maker_slip" in note
    assert slip < 100.0  # comfortably under the 150bps gate


def test_maker_lane_passes_gate_where_taker_would_fail(monkeypatch):
    from hermes.models import AllocationProposal

    monkeypatch.setenv("HERMES_PURE_MODE", "1")
    monkeypatch.setenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1")
    # ~256bps taker (would trip the 150 gate) but ~64bps as a maker.
    _patch_book(monkeypatch, mid=0.78, best_ask=0.80)
    sig = _sig()
    proposal = AllocationProposal(
        capital_usd=2000, weights={sig.substrategy_id: 0.5},
        diversification_ratio=1.2, concentration_hhi=0.5,
    )

    monkeypatch.delenv("HERMES_MAKER_MODE", raising=False)
    taker = pt.analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    assert taker.skip and any("slippage_gate" in r for r in taker.reasons)

    monkeypatch.setenv("HERMES_MAKER_MODE", "1")
    maker = pt.analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    assert not maker.skip
    assert maker.recommended_size_usd == pytest.approx(40.0)
