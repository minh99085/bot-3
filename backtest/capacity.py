"""C1 — capacity ceiling: how much $/week can this strategy actually absorb?

The prize must be judged against the effort. A 15m binary book a few hundred
dollars deep cannot pay for months of engineering no matter how real the edge
is. This module turns observed Polymarket order books + the fleet's observed
signal rate into an explicit $/week ceiling at sizes that do NOT move the
price:

  fillable/window/side = Σ (price × size) over levels within `max_impact`
                         of the best quote, × participation haircut
  ceiling $/week       = fillable/window × windows/week × observed signal rate

The participation haircut (take at most a fraction of visible depth) is the
same pessimism applied to paper fills (C2, hermes/fill_model.py): visible
depth is not YOUR depth — other takers exist, quotes fade, and adverse
selection eats the marginal fill.

Pure math + injectable books → unit-testable offline; scripts/capacity_report.py
feeds it live books on the VPS and writes the number to reports/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

# Take at most this fraction of visible depth (C2 uses the same constant —
# hermes/fill_model.py imports it; keep a single source of truth HERE).
PARTICIPATION_MAX = 0.25
# "Doesn't move the price" band: levels within this many probability-cents of
# the best quote. 1¢ on a 0.20–0.80 contract is 1.25–5% of price.
MAX_IMPACT_CENTS = 0.01

WINDOWS_PER_WEEK_15M = 4 * 24 * 7  # 672


@dataclass
class CapacityEstimate:
    fillable_yes_usd: float = 0.0     # per window, after participation haircut
    fillable_no_usd: float = 0.0
    per_window_usd: float = 0.0       # what one window can absorb (one side avg)
    signal_rate: float = 0.0          # fraction of windows the fleet fires on
    windows_per_week: int = WINDOWS_PER_WEEK_15M
    weekly_ceiling_usd: float = 0.0
    participation: float = PARTICIPATION_MAX
    max_impact_cents: float = MAX_IMPACT_CENTS
    notes: list[str] = field(default_factory=list)

    def text(self) -> str:
        lines = [
            "=== CAPACITY CEILING — btc-updown-15m, no-price-impact sizes ===",
            f"fillable/window: YES ${self.fillable_yes_usd:,.0f}  "
            f"NO ${self.fillable_no_usd:,.0f}  "
            f"(≤{self.max_impact_cents*100:.0f}¢ impact, "
            f"{self.participation:.0%} participation)",
            f"observed signal rate: {self.signal_rate:.1%} of windows",
            f"windows/week: {self.windows_per_week}",
            "",
            f">>> WEEKLY CEILING ≈ ${self.weekly_ceiling_usd:,.0f} <<<",
            "",
            "Judge the prize against the effort: this is the MOST the strategy",
            "can deploy per week without moving the book, assuming the edge is",
            "real (still unproven — see PREREGISTRATION.md).",
        ]
        for n in self.notes:
            lines.append(f"NOTE: {n}")
        return "\n".join(lines)


def fillable_usd(
    levels: Sequence[tuple[float, float]],
    *,
    max_impact_cents: float = MAX_IMPACT_CENTS,
    participation: float = PARTICIPATION_MAX,
) -> float:
    """USD absorbable from ``[(price, size_shares), ...]`` (best first) without
    walking more than ``max_impact_cents`` past the best level."""
    if not levels:
        return 0.0
    best = float(levels[0][0])
    total = 0.0
    for price, size in levels:
        price = float(price)
        size = float(size)
        if price <= 0 or size <= 0:
            continue
        if abs(price - best) > max_impact_cents + 1e-12:
            break
        total += price * size
    return total * participation


def estimate_signal_rate(
    window_ts_list: Sequence[int],
    *,
    windows_per_day: int = 96,
    days: float = 7.0,
) -> float:
    """Fraction of possible windows the fleet actually traded, from the ledger.

    ``window_ts_list`` = window_ts of every settled trade (any lane). Distinct
    windows ÷ total possible windows over the observed span (capped at
    ``days``). Honest denominator: possible windows, not traded windows.
    """
    distinct = sorted(set(int(w) for w in window_ts_list if w))
    if not distinct:
        return 0.0
    span_sec = max(0, distinct[-1] - distinct[0])
    span_days = min(days, max(span_sec / 86_400.0, 1.0 / windows_per_day))
    possible = max(1.0, span_days * windows_per_day)
    return min(1.0, len(distinct) / possible)


def estimate_capacity(
    yes_book: Sequence[tuple[float, float]],
    no_book: Sequence[tuple[float, float]],
    *,
    signal_rate: float,
    windows_per_week: int = WINDOWS_PER_WEEK_15M,
    max_impact_cents: float = MAX_IMPACT_CENTS,
    participation: float = PARTICIPATION_MAX,
) -> CapacityEstimate:
    """The headline number: $/week the strategy can absorb at no-impact sizes.

    ``yes_book`` / ``no_book`` are the ASK sides (what a buyer lifts) of each
    token, best-first. One trade per window takes ONE side, so per-window
    capacity is the average of the two sides (direction ~alternates).
    """
    est = CapacityEstimate(
        signal_rate=float(min(1.0, max(0.0, signal_rate))),
        windows_per_week=int(windows_per_week),
        participation=participation,
        max_impact_cents=max_impact_cents,
    )
    est.fillable_yes_usd = fillable_usd(
        yes_book, max_impact_cents=max_impact_cents, participation=participation
    )
    est.fillable_no_usd = fillable_usd(
        no_book, max_impact_cents=max_impact_cents, participation=participation
    )
    est.per_window_usd = (est.fillable_yes_usd + est.fillable_no_usd) / 2.0
    est.weekly_ceiling_usd = (
        est.per_window_usd * est.windows_per_week * est.signal_rate
    )
    if est.per_window_usd < 200.0:
        est.notes.append(
            f"book is THIN (${est.per_window_usd:,.0f}/window absorbable) — "
            "capacity, not modeling, is the binding constraint."
        )
    if est.signal_rate <= 0.0:
        est.notes.append("signal rate 0 — no trades observed; ceiling is 0 by construction.")
    est.notes.append(
        "Paper fills cannot model adverse selection; live capacity is likely "
        "LOWER than this ceiling (C2 haircut is a bound, not a promise)."
    )
    return est
