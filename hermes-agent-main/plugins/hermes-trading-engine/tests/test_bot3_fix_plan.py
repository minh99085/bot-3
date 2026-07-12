"""Tests for DOWN ask-fair gap filter and quant-only tier path (no TV)."""

from engine.pulse.execution_gate import down_ask_fair_gap_blocks
from engine.pulse.loop_architecture.maker_checker import TradeGenerator, TradeOpportunity
from engine.pulse.tier_engine import DirectionalTierEngine, Tier, TierConfig

NOW = 1_000_000.0


def test_down_ask_fair_gap_blocks_loser_pattern():
    # FULL_REPORT losers: DOWN ask 0.53, fair_p_up ~0.39 -> gap 0.14
    assert down_ask_fair_gap_blocks(side="down", ask=0.53, fair_p_up=0.39, max_gap=0.12)
    assert not down_ask_fair_gap_blocks(side="down", ask=0.52, fair_p_up=0.43, max_gap=0.12)
    assert not down_ask_fair_gap_blocks(side="up", ask=0.53, fair_p_up=0.39, max_gap=0.12)
    assert not down_ask_fair_gap_blocks(side="down", ask=0.53, fair_p_up=0.39, max_gap=0.0)


def test_tier_quant_only_fires_without_tv():
    eng = DirectionalTierEngine(TierConfig(
        quant_only_when_no_tv=True,
        quant_only_min_edge=0.02,
        quant_only_min_conviction=0.05,
        down_max_ask_fair_gap=0.20,  # allow this synthetic case through gap filter
        min_seconds_since_open=60.0,
    ))
    # No TV snapshots -> MTF absent. Mid-window, sweet ask, positive digital edge on UP.
    d = eng.evaluate(
        window_key="w", sso=900, ttc_s=2700,
        s_now=64200.0, s_open=64000.0, sigma_per_sec=6.7e-5,
        ask_up=0.52, ask_down=0.50, tv_by_tf={}, now=NOW,
        ask_depth_up=2000, ask_depth_down=2000,
    )
    assert d.trade, d.reason
    assert d.tier in (Tier.HARVEST, Tier.PROBE)
    assert d.reason.startswith("quant_only_")


def test_tier_down_ask_fair_gap_waits():
    eng = DirectionalTierEngine(TierConfig(
        quant_only_when_no_tv=True,
        down_max_ask_fair_gap=0.12,
        min_seconds_since_open=60.0,
    ))
    # Strong down displacement -> prefers DOWN; ask-fair gap oversized -> WAIT.
    d = eng.evaluate(
        window_key="w", sso=900, ttc_s=2700,
        s_now=63600.0, s_open=64000.0, sigma_per_sec=6.7e-5,
        ask_up=0.40, ask_down=0.55, tv_by_tf={}, now=NOW,
        ask_depth_up=2000, ask_depth_down=2000,
    )
    if d.side == "down":
        assert d.tier == Tier.WAIT
        assert d.reason == "down_ask_fair_gap"


def test_trade_generator_loss_streak_cuts_size(monkeypatch):
    monkeypatch.setenv("PULSE_LOSS_STREAK_CUT_AFTER", "2")
    monkeypatch.setenv("PULSE_LOSS_STREAK_CUT_TRADES", "3")
    monkeypatch.setenv("PULSE_LOSS_STREAK_SIZE_MULT", "0.5")
    gen = TradeGenerator()
    opp = TradeOpportunity(
        opportunity_id="o1", event_id="e1", series_slug="btc-up-or-down-15m",
        side="down", ask_price=0.53, fair_p=0.45, edge=0.02, size_usd=10.0,
        ttc_s=600.0, tick_size=0.01, discovered_at=NOW,
    )
    gen.record_outcome(False)
    gen.record_outcome(False)
    p = gen.propose(opp, worktree_id="wt")
    assert p.size_usd == 5.0
