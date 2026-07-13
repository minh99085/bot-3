"""Tests for PULSE_TRAINING_THROUGHPUT_MODE helpers."""

from __future__ import annotations

from engine.pulse.loop_architecture.asset_triage import (
    PROCEED_SWEEP,
    AssetTriageSkill,
    TriageConfig,
    TriageReject,
)
from engine.pulse.markets import OrderBook, PulseWindow
from engine.pulse.training_throughput import (
    paper_floor_outcome_prob,
    training_min_ev,
    training_throughput_enabled,
)


def test_training_throughput_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PULSE_TRAINING_THROUGHPUT_MODE", raising=False)
    assert not training_throughput_enabled()
    assert training_min_ev() == 0.0
    assert paper_floor_outcome_prob(0.40, 0.55) == 0.40


def test_training_min_ev_and_prob_floor(monkeypatch):
    monkeypatch.setenv("PULSE_TRAINING_THROUGHPUT_MODE", "1")
    monkeypatch.setenv("PULSE_EXEC_TRAINING_MIN_EV", "-0.05")
    assert training_throughput_enabled()
    assert training_min_ev() == -0.05
    assert paper_floor_outcome_prob(0.40, 0.55) == 0.555


def _window(ask: float = 0.50) -> PulseWindow:
    book = OrderBook(
        best_bid=ask - 0.02,
        best_ask=ask,
        ask_depth_usd=10000.0,
        bid_depth_usd=10000.0,
        asks=[(ask, 10000.0 / ask)],
        bids=[(ask - 0.02, 10000.0)],
    )
    return PulseWindow(
        event_id="evt-1",
        market_id="m1",
        slug="btc-up-or-down-hourly-test",
        title="BTC hourly",
        open_ts=1_000_000.0,
        close_ts=1_003_600.0,
        up_token_id="up-tok",
        down_token_id="dn-tok",
        series_slug="btc-up-or-down-hourly",
        up_book=book,
        down_book=book,
    )


def test_triage_synthetic_flat_without_tv_feature(monkeypatch):
    monkeypatch.setenv("PULSE_TRAINING_THROUGHPUT_MODE", "1")
    skill = AssetTriageSkill(cfg=TriageConfig(trend_source="price"))
    v = skill.evaluate(
        window=_window(0.50),
        side="up",
        ask_price=0.50,
        now=1_000_100.0,
        tv_feature=None,
        symbol="BTCUSD",
    )
    assert v.status == PROCEED_SWEEP


def test_triage_training_mode_bypasses_misaligned_trend(monkeypatch):
    monkeypatch.setenv("PULSE_TRAINING_THROUGHPUT_MODE", "1")
    monkeypatch.setenv("PULSE_TRIAGE_TREND_EXPLORATION_RATE", "0")
    skill = AssetTriageSkill(cfg=TriageConfig(trend_source="price"))
    v = skill.evaluate(
        window=_window(0.50),
        side="up",
        ask_price=0.50,
        now=1_000_100.0,
        tv_feature={
            "source": "price_action",
            "trend": "falling",
            "strength": 0.6,
            "timeframe": "spot",
        },
        symbol="BTCUSD",
    )
    assert v.status == PROCEED_SWEEP


def test_triage_without_training_rejects_no_tv(monkeypatch):
    monkeypatch.setenv("PULSE_TRAINING_THROUGHPUT_MODE", "0")
    skill = AssetTriageSkill(cfg=TriageConfig(trend_source="price"))
    v = skill.evaluate(
        window=_window(0.50),
        side="up",
        ask_price=0.50,
        now=1_000_100.0,
        tv_feature=None,
        symbol="BTCUSD",
    )
    assert v.status == TriageReject.NO_PRICE_TREND.value
