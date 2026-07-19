"""Paired lane scoreboard — rank strategy variants on SHARED windows.

All lanes trade btc-updown-15m, so any two lanes can be compared on the
windows BOTH settled: market luck cancels and the difference is strategy.
Ranking rules (pre-registered, see docker-compose header):

  * a lane must beat lane09 (random_null) on paired windows to count as
    anything but noise;
  * lane08 (legacy_ensemble) is expected to lose — if it wins, distrust the
    harness before trusting any winner;
  * promotion decisions use only windows AFTER the ranking was made
    (walk-forward) — this module reports, it does not promote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from backtest.paper_ledger import RealTrade, load_trades

NULL_LANE_HINT = "random"  # lane id containing this substring is the null


@dataclass
class LaneStats:
    lane: str
    n: int = 0
    wins: int = 0
    pnl: float = 0.0
    avg_entry: float = 0.0
    # paired-vs-null on common windows
    n_paired: int = 0
    paired_pnl_diff: float = 0.0  # this lane minus null, same windows

    @property
    def wr(self) -> float:
        return self.wins / self.n if self.n else 0.0


@dataclass
class LaneBoard:
    lanes: list[LaneStats] = field(default_factory=list)
    null_lane: Optional[str] = None
    n_shared_windows: int = 0
    notes: list[str] = field(default_factory=list)

    def text(self) -> str:
        lines = [
            "=== LANE SCOREBOARD — paired on shared btc15 windows ===",
            f"shared windows (all-lane intersection): {self.n_shared_windows}",
            "",
            f"{'lane':22s} {'n':>4s} {'WR':>7s} {'PnL$':>10s} {'avg_entry':>9s} "
            f"{'n_pair':>6s} {'Δpnl vs null':>12s}",
        ]
        for s in sorted(self.lanes, key=lambda x: -x.paired_pnl_diff):
            lines.append(
                f"{s.lane:22s} {s.n:>4d} {s.wr:>6.1%} {s.pnl:>10.2f} "
                f"{s.avg_entry:>9.3f} {s.n_paired:>6d} {s.paired_pnl_diff:>+12.2f}"
            )
        for n in self.notes:
            lines.append(f"NOTE: {n}")
        return "\n".join(lines)


def _by_window(trades: Sequence[RealTrade]) -> dict[int, RealTrade]:
    """One trade per window (first fill wins) keyed by window_ts."""
    out: dict[int, RealTrade] = {}
    for t in trades:
        out.setdefault(t.window_ts, t)
    return out


def build_board(trades_by_lane: dict[str, list[RealTrade]]) -> LaneBoard:
    board = LaneBoard()
    null_lane = next(
        (k for k in trades_by_lane if NULL_LANE_HINT in k.lower()), None
    )
    board.null_lane = null_lane
    null_windows = _by_window(trades_by_lane.get(null_lane, [])) if null_lane else {}

    window_sets = [
        {t.window_ts for t in ts} for ts in trades_by_lane.values() if ts
    ]
    board.n_shared_windows = (
        len(set.intersection(*window_sets)) if len(window_sets) > 1 else 0
    )

    for lane, trades in sorted(trades_by_lane.items()):
        s = LaneStats(lane=lane)
        s.n = len(trades)
        s.wins = sum(1 for t in trades if t.won)
        s.pnl = sum(t.pnl_usd for t in trades)
        s.avg_entry = (
            sum(t.p_side for t in trades) / s.n if s.n else 0.0
        )
        if null_lane and lane != null_lane:
            mine = _by_window(trades)
            common = set(mine) & set(null_windows)
            s.n_paired = len(common)
            s.paired_pnl_diff = sum(
                mine[w].pnl_usd - null_windows[w].pnl_usd for w in common
            )
        board.lanes.append(s)

    if null_lane is None:
        board.notes.append(
            "no random_null lane found — paired comparison unavailable"
        )
    legacy = next((s for s in board.lanes if "legacy" in s.lane.lower()), None)
    if legacy and legacy.n >= 30 and legacy.paired_pnl_diff > 0:
        board.notes.append(
            "legacy_ensemble (negative control) is BEATING null — "
            "distrust the harness before trusting any winner."
        )
    small = [s.lane for s in board.lanes if 0 < s.n < 30]
    if small:
        board.notes.append(f"lanes below 30 trades (noise): {small}")
    return board


def board_from_ledgers(root: Path | str) -> LaneBoard:
    root = Path(root)
    trades_by_lane: dict[str, list[RealTrade]] = {}
    for ledger in sorted(root.glob("*/trade_ledger.jsonl")):
        lane = ledger.parent.name
        trades_by_lane[lane] = load_trades([ledger])
    return build_board(trades_by_lane)
