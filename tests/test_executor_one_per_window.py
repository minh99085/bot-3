"""Executor guard: one position per market window per lane (no pyramiding)."""

from __future__ import annotations

import pytest

from hermes.models import (
    ConfidenceTier,
    Direction,
    EntryMode,
    Regime,
    Signal,
    VerificationReport,
    VerifierDecision,
)


def _signal(slug: str, market_id: str) -> Signal:
    return Signal(
        market_id=market_id,
        slug=slug,
        question=f"{slug}?",
        direction=Direction.DOWN,
        entry_mode=EntryMode.MEAN_REVERSION,
        confidence_tier=ConfidenceTier.B,
        conviction=0.8,
        fair_value=0.6,
        market_price=0.5,
        expected_edge=0.1,
        regime=Regime.MEAN_REVERT,
        hourly_bucket=12,
        size_usd_suggested=40.0,
        market_series="btc_updown_15m",
        timeframe="15m",
    )


def _pass_report(signal: Signal) -> VerificationReport:
    return VerificationReport(
        signal_id=signal.signal_id,
        decision=VerifierDecision.PASS,
        sized_usd=40.0,
    )


@pytest.fixture(autouse=True)
def _isolated_ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_INSTANCE_ID", "lane_test")
    monkeypatch.setenv("HERMES_PAPER_DIR", str(tmp_path / "paper_lane_test"))
    monkeypatch.setenv("HERMES_HANDOFF_DIR", str(tmp_path / "handoff_lane_test"))
    monkeypatch.setenv("HERMES_PAPER_ONLY", "1")
    monkeypatch.delenv("HERMES_ALLOW_SAME_SLUG", raising=False)


def test_skips_second_signal_same_window():
    from hermes.executor import executor_tick

    slug = "btc-updown-15m-1784730600"
    s1 = _signal(slug, market_id="3017574")
    s2 = _signal(slug, market_id="3017574")

    first = executor_tick(signals=[s1], reports=[_pass_report(s1)], turn_id="t1")
    assert len(first) == 1

    # A later tick for the SAME still-open window must not add another fill.
    second = executor_tick(signals=[s2], reports=[_pass_report(s2)], turn_id="t2")
    assert second == []


def test_skips_duplicate_within_single_tick():
    from hermes.executor import executor_tick

    slug = "btc-updown-15m-1784730600"
    s1 = _signal(slug, market_id="3017574")
    s2 = _signal(slug, market_id="3017574")

    fills = executor_tick(
        signals=[s1, s2],
        reports=[_pass_report(s1), _pass_report(s2)],
        turn_id="t1",
    )
    assert len(fills) == 1


def test_allows_distinct_windows():
    from hermes.executor import executor_tick

    s1 = _signal("btc-updown-15m-1784730600", market_id="3017574")
    s2 = _signal("btc-updown-15m-1784731500", market_id="3017999")

    fills = executor_tick(
        signals=[s1, s2],
        reports=[_pass_report(s1), _pass_report(s2)],
        turn_id="t1",
    )
    assert len(fills) == 2


def test_opt_in_allows_pyramiding(monkeypatch):
    from hermes.executor import executor_tick

    monkeypatch.setenv("HERMES_ALLOW_SAME_SLUG", "1")
    slug = "btc-updown-15m-1784730600"
    s1 = _signal(slug, market_id="3017574")
    s2 = _signal(slug, market_id="3017574")

    fills = executor_tick(
        signals=[s1, s2],
        reports=[_pass_report(s1), _pass_report(s2)],
        turn_id="t1",
    )
    assert len(fills) == 2
