"""Tests for fast BTC pretrade sizing ladder."""

from __future__ import annotations

from hermes.models import (
    AllocationProposal,
    ConfidenceTier,
    Direction,
    EntryMode,
    Regime,
    Signal,
)
from hermes.pretrade import analyze_signal
from hermes.substrategy import annotate_signal


def _sig(slug: str, **kw) -> Signal:
    base = dict(
        market_id="mkt_btc",
        slug=slug,
        question="Bitcoin Up or Down",
        direction=Direction.DOWN,
        entry_mode=EntryMode.MEAN_REVERSION,
        confidence_tier=ConfidenceTier.A,
        conviction=0.8,
        fair_value=0.55,
        market_price=0.48,
        expected_edge=0.09,
        live_ev=0.075,
        regime=Regime.MEAN_REVERT,
        hourly_bucket=14,
        size_usd_suggested=50.0,
        entry_vwap_target=0.485,
        pre_entry_stability_ok=True,
        timeframe="5m" if "5m" in slug else "15m",
        oracle_alignment=0.8,
        meta={"paper": True, "asset": "BTC", "oracle_return_proxy": -0.001},
    )
    base.update(kw)
    return annotate_signal(Signal(**base))


def test_fast_market_cold_start_small_size(monkeypatch):
    monkeypatch.setenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1")
    sig = _sig("btc-updown-5m-1784113500")
    proposal = AllocationProposal(
        capital_usd=2000,
        weights={sig.substrategy_id: 0.5},
        diversification_ratio=1.2,
        concentration_hhi=0.5,
    )
    analysis = analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    assert not analysis.skip or analysis.recommended_size_usd == 0
    if not analysis.skip:
        # Cold start ≤ 0.5% of bankroll (~$10) up to bumped min ticket
        assert analysis.recommended_size_usd <= 2000 * 0.02 + 0.01
        assert analysis.recommended_size_pct <= 2.0


def test_out_of_scope_skipped(monkeypatch):
    monkeypatch.setenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1")
    sig = _sig("will-bitcoin-hit-1m", timeframe="1h", market_series="btc")
    # force non-scoped series
    sig.market_series = "btc"
    sig.substrategy_id = "btc|mean_reversion|mean_revert|h14|1h"
    proposal = AllocationProposal(
        capital_usd=2000,
        weights={sig.substrategy_id: 0.5},
        diversification_ratio=1.2,
        concentration_hhi=0.5,
    )
    analysis = analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    # Either skipped by scope or by EV — must not size a non-scoped market as fast
    assert analysis.skip or "out_of_scope" in " ".join(analysis.reasons)
