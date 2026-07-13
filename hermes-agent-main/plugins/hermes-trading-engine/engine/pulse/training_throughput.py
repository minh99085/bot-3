"""Training throughput helpers — paper learning mode (PAPER ONLY).

When PULSE_TRAINING_THROUGHPUT_MODE=1, relax restrict-only gates so the bot
collects settlements for CHRONOS/Selectivity replay without starving fills.
Does NOT disable execution_gate VWAP checks; floors prob at ask for paper EV.
"""

from __future__ import annotations

import os


def training_throughput_enabled() -> bool:
    return (os.getenv("PULSE_TRAINING_THROUGHPUT_MODE", "0") or "0").strip().lower() in (
        "1", "true", "yes", "on")


def training_min_ev() -> float:
    """Paper execution EV floor (may be slightly negative for learning throughput)."""
    if not training_throughput_enabled():
        return 0.0
    try:
        return float(os.getenv("PULSE_EXEC_TRAINING_MIN_EV", "-0.03") or -0.03)
    except (TypeError, ValueError):
        return -0.03


def paper_floor_outcome_prob(outcome_prob: float, ask: float) -> float:
    """Floor model P(win) at ask so paper EV = p − vwap is not artificially negative."""
    if not training_throughput_enabled():
        return float(outcome_prob)
    try:
        p = float(outcome_prob)
        a = float(ask)
    except (TypeError, ValueError):
        return float(outcome_prob)
    if a <= 0 or a >= 1:
        return p
    # Small buffer above ask covers taker fee in thin books.
    return max(p, min(0.99, a + 0.005))
