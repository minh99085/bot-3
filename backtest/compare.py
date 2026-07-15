"""Naive misprice-only vs full enhanced stack — same universe, clear lift."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from backtest.engine import BacktestEngine
from backtest.metrics import MetricsReport, compute_metrics
from backtest.synthetic_generator import SyntheticDataGenerator
from models.config import EnhancedMispriceConfig, load_enhanced_config

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    enhanced: MetricsReport
    naive: MetricsReport
    wr_lift: float
    dd_delta: float
    plain_english: str

    def to_dict(self) -> dict:
        return {
            "enhanced": self.enhanced.to_dict(),
            "naive": self.naive.to_dict(),
            "wr_lift": self.wr_lift,
            "dd_delta": self.dd_delta,
            "plain_english": self.plain_english,
        }

    def summary_text(self) -> str:
        return (
            "=== Naive vs Enhanced ===\n"
            f"Naive    WR={self.naive.win_rate:.1%}  DD={self.naive.max_drawdown_pct:.1%}  "
            f"n={self.naive.n_trades}  PF={self.naive.profit_factor:.2f}\n"
            f"Enhanced WR={self.enhanced.win_rate:.1%}  DD={self.enhanced.max_drawdown_pct:.1%}  "
            f"n={self.enhanced.n_trades}  PF={self.enhanced.profit_factor:.2f}\n"
            f"WR lift: {self.wr_lift:+.1%}   DD delta: {self.dd_delta:+.1%}\n\n"
            f"{self.plain_english}"
        )


def compare_naive_vs_enhanced(
    *,
    config: Optional[EnhancedMispriceConfig] = None,
    n_markets: int = 8000,
    seed: int = 42,
) -> ComparisonResult:
    cfg = config or load_enhanced_config()
    uni = SyntheticDataGenerator(cfg, seed=seed).generate(n_markets=n_markets)
    decisions = uni.chronological()

    enh = BacktestEngine(cfg, mode="enhanced", seed=seed).run_on_decisions(
        decisions, n_markets=uni.n_markets, seed=seed
    )
    naive = BacktestEngine(cfg, mode="naive", seed=seed).run_on_decisions(
        decisions, n_markets=uni.n_markets, seed=seed
    )
    me = compute_metrics(enh)
    mn = compute_metrics(naive)
    lift = me.win_rate - mn.win_rate
    dd_delta = me.max_drawdown_pct - mn.max_drawdown_pct
    plain = (
        f"On the same {uni.n_markets} synthetic markets, the full stack "
        f"(Beta conviction + Kelly + risk budget) improved win rate by {100 * lift:.1f} "
        f"percentage points vs naive edge-only fixed sizing "
        f"({100 * mn.win_rate:.1f}% → {100 * me.win_rate:.1f}%). "
        "The lift comes from skipping mid-odds / low-conviction bets that naive trading still takes."
    )
    logger.info("Compare WR naive=%.1f%% enhanced=%.1f%% lift=%+.1fpp", 100 * mn.win_rate, 100 * me.win_rate, 100 * lift)
    return ComparisonResult(
        enhanced=me, naive=mn, wr_lift=lift, dd_delta=dd_delta, plain_english=plain
    )
