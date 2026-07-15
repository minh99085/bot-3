"""Pre-trade sizing unit tests."""

from __future__ import annotations

from hermes.models import (
    AllocationProposal,
    ConfidenceTier,
    Direction,
    EntryMode,
    Regime,
    Signal,
)
from hermes.pretrade import analyze_signal, apply_pretrade_to_signal


def _sig(**kw) -> Signal:
    base = dict(
        market_id="mkt_btc_5m",
        slug="btc-updown-5m",
        question="Bitcoin Up or Down - 5 Minutes",
        direction=Direction.NO,
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
        market_series="btc_updown_5m",
        timeframe="5m",
        oracle_alignment=0.8,
        meta={"paper": True, "asset": "BTC", "oracle_return_proxy": -0.001},
    )
    base.update(kw)
    return Signal(**base)


def test_pretrade_sizes_pct_of_bankroll():
    sig = _sig()
    proposal = AllocationProposal(
        capital_usd=2000,
        weights={sig.substrategy_id or "btc_updown_5m|mean_reversion|mean_revert|h14|5m": 0.2},
        diversification_ratio=1.5,
        concentration_hhi=0.2,
    )
    # Ensure substrategy id set
    from hermes.substrategy import annotate_signal

    sig = annotate_signal(sig)
    proposal.weights = {sig.substrategy_id: 0.2}
    analysis = analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    assert analysis.bankroll_usd == 2000.0
    if not analysis.skip:
        assert 0 < analysis.recommended_size_pct <= 3.0
        assert analysis.recommended_size_usd <= 2000 * 0.03 + 0.01
        updated = apply_pretrade_to_signal(sig, analysis)
        assert updated.allocation_usd == analysis.recommended_size_usd


def test_pretrade_skips_low_ev():
    sig = _sig(expected_edge=0.02, live_ev=0.01)
    from hermes.substrategy import annotate_signal

    sig = annotate_signal(sig)
    proposal = AllocationProposal(
        capital_usd=2000,
        weights={sig.substrategy_id: 0.2},
        diversification_ratio=1.5,
        concentration_hhi=0.2,
    )
    analysis = analyze_signal(sig, proposal, bankroll=2000.0, lessons="", paper=True)
    assert analysis.skip is True
    assert analysis.recommended_size_usd == 0.0
