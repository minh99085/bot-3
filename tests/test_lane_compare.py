"""Paired lane scoreboard tests (synthetic ledgers)."""

from __future__ import annotations

import json

from backtest.lane_compare import board_from_ledgers, build_board
from backtest.paper_ledger import RealTrade


def _t(window_ts, won, pnl, entry=0.5):
    return RealTrade(
        slug=f"btc-updown-15m-{window_ts}", asset="btc", timeframe="15m",
        window_ts=window_ts, settled_at="t", direction="UP",
        p_side=entry, won=won, pnl_usd=pnl, size_usd=100.0,
    )


def test_paired_diff_vs_null_cancels_market_luck():
    # Null loses both windows; lane A wins the same two windows.
    lanes = {
        "lane01_baseline": [_t(1000, True, 100), _t(2000, True, 100)],
        "lane09_random": [_t(1000, False, -100), _t(2000, False, -100)],
    }
    board = build_board(lanes)
    a = next(s for s in board.lanes if s.lane == "lane01_baseline")
    assert a.n_paired == 2
    assert a.paired_pnl_diff == 400.0  # (100-(-100)) * 2
    assert board.null_lane == "lane09_random"


def test_unpaired_windows_excluded_from_diff():
    lanes = {
        "lane01_baseline": [_t(1000, True, 100), _t(3000, True, 999)],  # 3000 not in null
        "lane09_random": [_t(1000, False, -100), _t(2000, True, 50)],
    }
    board = build_board(lanes)
    a = next(s for s in board.lanes if s.lane == "lane01_baseline")
    assert a.n_paired == 1
    assert a.paired_pnl_diff == 200.0  # only window 1000 counts


def test_legacy_beating_null_raises_harness_warning():
    legacy = [_t(i, True, 50) for i in range(40)]
    null = [_t(i, False, -50) for i in range(40)]
    board = build_board({"lane08_legacy": legacy, "lane09_random": null})
    assert any("distrust the harness" in n for n in board.notes)


def test_board_from_ledgers_reads_lane_dirs(tmp_path):
    for lane, won in (("lane01_baseline", True), ("lane09_random", False)):
        d = tmp_path / lane
        d.mkdir()
        rec = {
            "event": "settlement", "slug": "btc-updown-15m-1784000000",
            "direction": "UP", "entry_price": 0.5, "won": won,
            "pnl_usd": 100 if won else -100, "size_usd": 100.0, "notes": "x",
        }
        (d / "trade_ledger.jsonl").write_text(json.dumps(rec))
    board = board_from_ledgers(tmp_path)
    assert len(board.lanes) == 2
    text = board.text()
    assert "lane01_baseline" in text and "Δpnl vs null" in text
