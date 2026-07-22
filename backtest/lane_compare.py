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
    # B3 pre-registered stats (sign test vs null, Holm-corrected)
    p_value: Optional[float] = None
    significant_holm: Optional[bool] = None

    @property
    def wr(self) -> float:
        return self.wins / self.n if self.n else 0.0


@dataclass
class LaneBoard:
    lanes: list[LaneStats] = field(default_factory=list)
    null_lane: Optional[str] = None
    n_shared_windows: int = 0
    notes: list[str] = field(default_factory=list)
    # B3 — verdicts are blocked until the pre-registered horizon is met.
    verdict_allowed: bool = False
    verdict_msg: str = ""

    def text(self) -> str:
        lines = [
            "=== LANE SCOREBOARD — paired on shared btc15 windows ===",
            f"shared windows (all-lane intersection): {self.n_shared_windows}",
        ]
        if self.verdict_msg:
            lines.append(f"*** {self.verdict_msg} ***")
        lines += [
            "",
            f"{'lane':22s} {'n':>4s} {'WR':>7s} {'PnL$':>10s} {'avg_entry':>9s} "
            f"{'n_pair':>6s} {'Δpnl vs null':>12s} {'p(sign)':>8s} {'Holm':>5s}",
        ]
        for s in sorted(self.lanes, key=lambda x: -x.paired_pnl_diff):
            p_txt = f"{s.p_value:.3f}" if s.p_value is not None else "—"
            sig_txt = (
                "—" if s.significant_holm is None
                else ("SIG" if s.significant_holm else "ns")
            )
            lines.append(
                f"{s.lane:22s} {s.n:>4d} {s.wr:>6.1%} {s.pnl:>10.2f} "
                f"{s.avg_entry:>9.3f} {s.n_paired:>6d} {s.paired_pnl_diff:>+12.2f} "
                f"{p_txt:>8s} {sig_txt:>5s}"
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

    paired_diffs_by_lane: dict[str, list[float]] = {}
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
            diffs = [mine[w].pnl_usd - null_windows[w].pnl_usd for w in common]
            s.paired_pnl_diff = sum(diffs)
            paired_diffs_by_lane[lane] = diffs
        board.lanes.append(s)

    # ── B3 pre-registered statistics ────────────────────────────────────────
    from backtest.prereg import (
        PRIMARY_LANE_HINT,
        holm_bonferroni,
        paired_sign_pvalue,
        regime_shift_flag,
        verdict_gate,
    )

    pvals: dict[str, float] = {}
    for lane, diffs in paired_diffs_by_lane.items():
        p = paired_sign_pvalue(diffs)
        if p is not None:
            pvals[lane] = p
    sig = holm_bonferroni(pvals) if pvals else {}
    for s in board.lanes:
        if s.lane in pvals:
            s.p_value = pvals[s.lane]
            s.significant_holm = sig.get(s.lane)

    # Verdict gate keys off the PRIMARY lane's pre-registered horizon.
    primary = next(
        (s for s in board.lanes if PRIMARY_LANE_HINT in s.lane.lower()), None
    )
    board.verdict_allowed, board.verdict_msg = verdict_gate(
        primary.n if primary else 0, primary.n_paired if primary else 0
    )

    # Non-stationarity: pooled realized |window move| early vs late.
    moves: list[tuple[int, float]] = []
    for trades in trades_by_lane.values():
        for t in trades:
            if t.entry_cex and t.exit_cex and t.entry_cex > 0:
                moves.append((t.window_ts, abs(t.exit_cex / t.entry_cex - 1.0)))
    flag = regime_shift_flag(moves)
    if flag:
        board.notes.append(flag)

    # SETTLEMENT CONSISTENCY INVARIANT — same window + same direction must
    # yield the same outcome in every lane. A violation means the harness is
    # mismeasuring (caught live: post-close drift used as exit reference).
    by_window_dir: dict[tuple[int, str], set[bool]] = {}
    for lane, trades in trades_by_lane.items():
        for t in trades:
            by_window_dir.setdefault((t.window_ts, t.direction.upper()), set()).add(t.won)
    bad = [k for k, outcomes in by_window_dir.items() if len(outcomes) > 1]
    if bad:
        board.notes.append(
            f"CRITICAL settlement inconsistency: {len(bad)} window/direction "
            f"groups with conflicting outcomes (e.g. {bad[:3]}) — harness is "
            "mismeasuring; fix before trusting ANY lane ranking."
        )

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
