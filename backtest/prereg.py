"""B3 — pre-registered statistics for the lane experiment.

The scoreboard was an invitation to fool ourselves: 10 lanes, peeking every
few hours, no correction — SOMETHING will always look like a winner. This
module enforces the analysis plan in knowledge/PREREGISTRATION.md:

  * ONE primary hypothesis, fixed BEFORE the data (lane01 pure barrier beats
    the random null on paired windows);
  * a fixed horizon — NO verdict of any kind before the sample threshold;
  * Holm–Bonferroni across every lane-vs-null comparison (family α = 0.05);
  * a non-stationarity flag when early and late samples span different vol
    regimes (a "winner" that only won in one regime is not a winner).

Pure math — no I/O, no network. lane_compare wires it into the board.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

# Pre-registered horizon (see knowledge/PREREGISTRATION.md — do not tune):
VERDICT_MIN_TRADES = 1000   # resolved trades in the primary lane
VERDICT_MIN_PAIRED = 300    # paired-with-null windows for any lane-vs-null claim
FAMILY_ALPHA = 0.05
PRIMARY_LANE_HINT = "lane01"  # lane01_baseline = pure barrier (H1)

# Non-stationarity: early-vs-late median |window move| ratio outside this band
# means the sample spans different vol regimes.
REGIME_RATIO_LO = 0.5
REGIME_RATIO_HI = 2.0


def paired_sign_pvalue(diffs: Sequence[float]) -> Optional[float]:
    """Two-sided exact sign test on paired differences (ties dropped).

    Nonparametric on purpose: longshot PnL is wildly non-normal, so a t-test
    on $ differences would be dishonest. Returns None when nothing to test.
    """
    nonzero = [d for d in diffs if abs(d) > 1e-12]
    m = len(nonzero)
    if m == 0:
        return None
    k = sum(1 for d in nonzero if d > 0)
    # P(X <= min(k, m-k)) under Bin(m, 0.5), doubled (two-sided), capped at 1.
    lo = min(k, m - k)
    tail = sum(math.comb(m, i) for i in range(0, lo + 1)) / (2.0 ** m)
    return min(1.0, 2.0 * tail)


def holm_bonferroni(
    pvals: dict[str, float], alpha: float = FAMILY_ALPHA
) -> dict[str, bool]:
    """Step-down Holm correction: {name: significant?} at family level α."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, bool] = {}
    blocked = False
    for i, (name, p) in enumerate(items):
        threshold = alpha / (m - i)
        if blocked or p > threshold:
            blocked = True
            out[name] = False
        else:
            out[name] = True
    return out


def verdict_gate(n_trades: int, n_paired: int) -> tuple[bool, str]:
    """May ANY winner/loser verdict be stated yet? Pre-registered, not tunable."""
    if n_trades >= VERDICT_MIN_TRADES and n_paired >= VERDICT_MIN_PAIRED:
        return True, (
            f"horizon met (primary n={n_trades}>={VERDICT_MIN_TRADES}, "
            f"paired={n_paired}>={VERDICT_MIN_PAIRED})"
        )
    return False, (
        f"VERDICT LOCKED — pre-registered horizon not met: primary lane "
        f"n={n_trades}/{VERDICT_MIN_TRADES} resolved, paired-with-null "
        f"{n_paired}/{VERDICT_MIN_PAIRED}. Rankings below are DESCRIPTIVE ONLY."
    )


def regime_shift_flag(
    window_moves: Sequence[tuple[int, float]],
) -> Optional[str]:
    """Flag early-vs-late vol-regime drift.

    ``window_moves`` = (window_ts, |close/open - 1|) per settled window. The
    sample is split at the time midpoint; if median |move| differs by more
    than [0.5x, 2x] the early and late halves are different regimes and any
    aggregate verdict conflates them.
    """
    moves = [(ts, abs(m)) for ts, m in window_moves if m == m]  # drop NaN
    if len(moves) < 20:
        return None
    moves.sort(key=lambda x: x[0])
    half = len(moves) // 2
    early = sorted(m for _, m in moves[:half])
    late = sorted(m for _, m in moves[half:])
    med_early = early[len(early) // 2]
    med_late = late[len(late) // 2]
    if med_early <= 0 or med_late <= 0:
        return None
    ratio = med_late / med_early
    if ratio < REGIME_RATIO_LO or ratio > REGIME_RATIO_HI:
        return (
            f"NON-STATIONARY sample: late-half median |move| is {ratio:.2f}x the "
            f"early half — early and late trades span different vol regimes; "
            "aggregate rankings conflate them."
        )
    return None
