"""Backtest suite — PLUMBING SANITY CHECKS ONLY.

These tests verify the machinery (generator → engine → metrics) runs, tracks
every decision, and conserves cash. They deliberately assert NOTHING about
synthetic win rate: synthetic performance is not evidence of edge, and the
old ≥80%-WR gates here were enshrining a circular harness. The honesty
guardrails live in tests/test_synthetic_honesty.py; go/no-go is judged only
on real out-of-sample performance after costs.
"""

from __future__ import annotations

import pytest

from backtest.compare import compare_naive_vs_enhanced
from backtest.engine import BacktestEngine, run_backtest
from backtest.metrics import compute_metrics, threshold_sweep
from backtest.synthetic_generator import SyntheticDataGenerator
from models.config import load_enhanced_config


def test_synthetic_generator_multi_decision_and_chronology():
    cfg = load_enhanced_config()
    uni = SyntheticDataGenerator(cfg, seed=42).generate(n_markets=300)
    assert uni.n_markets == 300
    assert len(uni.decisions) == 300 * len(cfg.decision_fracs)
    chrono = uni.chronological()
    assert all(
        chrono[i].decision_time <= chrono[i + 1].decision_time
        for i in range(len(chrono) - 1)
    )


def test_engine_runs_tracks_and_conserves_cash():
    cfg = load_enhanced_config(mode="strict_real")
    er = BacktestEngine(cfg, mode="enhanced", seed=42).run_synthetic(
        n_markets=300, seed=42
    )
    m = compute_metrics(er)
    # Every decision tracked
    assert m.n_decisions == er.n_decision_points
    assert m.n_taken + m.n_rejected == m.n_decisions
    # Cash conservation: starting bankroll + total PnL == final cash
    total_pnl = sum(t.pnl_usd for t in er.trades)
    assert er.final_cash == pytest.approx(cfg.bankroll + total_pnl, rel=1e-9)
    # Synthetic runs are labeled as such all the way through
    assert er.data_source == "synthetic"
    assert m.data_source == "synthetic"
    assert "SANITY" in m.summary_text().upper()


def test_naive_vs_enhanced_compare_runs():
    cfg = load_enhanced_config(mode="strict_real")
    cmp = compare_naive_vs_enhanced(n_markets=300, seed=42, config=cfg)
    # Structural comparison only — no synthetic WR gate (that was the red flag).
    assert cmp.enhanced.n_decisions == cmp.naive.n_decisions
    assert cmp.enhanced.n_trades >= 0 and cmp.naive.n_trades >= 0


def test_threshold_sweep_monotonic_ish():
    cfg = load_enhanced_config(mode="strict_real")
    er = BacktestEngine(cfg, mode="enhanced", seed=7).run_synthetic(
        n_markets=300, seed=7
    )
    rows = threshold_sweep(er.decisions)
    assert rows
    # Higher threshold should not explode n without bound
    assert rows[-1]["n"] <= rows[0]["n"] + 1e-9


def test_run_backtest_compat_wrapper():
    cfg = load_enhanced_config(mode="strict_real")
    result = run_backtest(config=cfg, use_synthetic=True, n_markets=300, seed=42)
    assert result.engine is not None
    assert result.engine.data_source == "synthetic"
    assert result.report.n_trades == len(result.engine.trades)
