"""B3 — pre-registered stats: sign test, Holm, verdict lock, regime flag."""

from __future__ import annotations

import pytest

from backtest.lane_compare import build_board
from backtest.paper_ledger import RealTrade
from backtest.prereg import (
    VERDICT_MIN_PAIRED,
    VERDICT_MIN_TRADES,
    holm_bonferroni,
    paired_sign_pvalue,
    regime_shift_flag,
    verdict_gate,
)


def _trade(lane_seed: int, window_ts: int, won: bool, pnl: float,
           entry_cex: float = 64000.0, exit_cex: float = 64100.0) -> RealTrade:
    return RealTrade(
        slug=f"btc-updown-15m-{window_ts}", asset="btc", timeframe="15m",
        window_ts=window_ts, settled_at="t", direction="UP",
        p_side=0.5, won=won, pnl_usd=pnl, size_usd=40.0,
        entry_cex=entry_cex, exit_cex=exit_cex,
    )


# ── sign test ────────────────────────────────────────────────────────────────

def test_sign_test_all_positive_is_significant():
    p = paired_sign_pvalue([1.0] * 12)
    assert p is not None and p < 0.001


def test_sign_test_balanced_is_null():
    p = paired_sign_pvalue([1.0, -1.0] * 10)
    assert p == pytest.approx(1.0, abs=0.15)


def test_sign_test_drops_ties_and_handles_empty():
    assert paired_sign_pvalue([0.0, 0.0]) is None
    assert paired_sign_pvalue([]) is None
    assert paired_sign_pvalue([0.0, 2.0, 2.0, 2.0, 2.0, 2.0]) == pytest.approx(
        2 * (1 / 2**5), abs=1e-9
    )


# ── Holm–Bonferroni ─────────────────────────────────────────────────────────

def test_holm_all_pass_when_small_enough():
    sig = holm_bonferroni({"a": 0.001, "b": 0.02, "c": 0.04}, alpha=0.05)
    assert sig == {"a": True, "b": True, "c": True}  # 0.0167/0.025/0.05 ladder


def test_holm_step_down_blocks_after_first_failure():
    sig = holm_bonferroni({"a": 0.001, "b": 0.03, "c": 0.04}, alpha=0.05)
    # b fails 0.03 > 0.025 → c is blocked even though 0.04 <= 0.05
    assert sig == {"a": True, "b": False, "c": False}


def test_holm_controls_a_lone_marginal_p_across_ten_lanes():
    pvals = {f"lane{i:02d}": 0.04 for i in range(10)}
    sig = holm_bonferroni(pvals, alpha=0.05)
    assert not any(sig.values())  # 0.04 > 0.05/10 — ten peeks buy nothing


# ── verdict gate ─────────────────────────────────────────────────────────────

def test_verdict_locked_below_horizon():
    allowed, msg = verdict_gate(999, VERDICT_MIN_PAIRED)
    assert not allowed and "VERDICT LOCKED" in msg
    allowed, msg = verdict_gate(VERDICT_MIN_TRADES, VERDICT_MIN_PAIRED - 1)
    assert not allowed


def test_verdict_opens_at_horizon():
    allowed, msg = verdict_gate(VERDICT_MIN_TRADES, VERDICT_MIN_PAIRED)
    assert allowed and "horizon met" in msg


# ── regime flag ──────────────────────────────────────────────────────────────

def test_regime_flag_fires_on_vol_shift():
    early = [(1000 + i, 0.001) for i in range(15)]
    late = [(2000 + i, 0.01) for i in range(15)]   # 10x the median move
    flag = regime_shift_flag(early + late)
    assert flag is not None and "NON-STATIONARY" in flag


def test_regime_flag_quiet_when_homogeneous():
    moves = [(1000 + i, 0.003) for i in range(40)]
    assert regime_shift_flag(moves) is None


def test_regime_flag_needs_minimum_sample():
    assert regime_shift_flag([(1, 0.001), (2, 0.5)]) is None


# ── board integration ────────────────────────────────────────────────────────

def test_board_locks_verdict_and_reports_pvalues():
    win = {
        "lane01_baseline": [
            _trade(1, 1000 + i * 900, won=True, pnl=10.0) for i in range(40)
        ],
        "lane09_random": [
            _trade(9, 1000 + i * 900, won=False, pnl=-40.0) for i in range(40)
        ],
    }
    board = build_board(win)
    text = board.text()
    assert board.verdict_allowed is False
    assert "VERDICT LOCKED" in text and "DESCRIPTIVE ONLY" in text
    lane01 = next(s for s in board.lanes if s.lane == "lane01_baseline")
    assert lane01.p_value is not None and lane01.p_value < 0.001
    assert lane01.significant_holm is True  # only one comparison in family
    assert "p(sign)" in text


def test_board_regime_note_appears():
    calm = [
        _trade(1, 1000 + i * 900, won=True, pnl=5.0,
               entry_cex=64000.0, exit_cex=64000.0 * 1.0005)
        for i in range(15)
    ]
    wild = [
        _trade(1, 100000 + i * 900, won=True, pnl=5.0,
               entry_cex=64000.0, exit_cex=64000.0 * 1.02)
        for i in range(15)
    ]
    board = build_board({"lane01_baseline": calm + wild})
    assert any("NON-STATIONARY" in n for n in board.notes)
