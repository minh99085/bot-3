"""Monte Carlo robustness — many seeds, report WR distribution."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from backtest.engine import BacktestEngine, EngineResult
from backtest.metrics import MetricsReport, compute_metrics
from models.config import EnhancedMispriceConfig, load_enhanced_config

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloSummary:
    n_runs: int
    win_rates: list[float] = field(default_factory=list)
    max_dds: list[float] = field(default_factory=list)
    n_trades: list[int] = field(default_factory=list)
    mean_wr: float = 0.0
    median_wr: float = 0.0
    p5_wr: float = 0.0
    p95_wr: float = 0.0
    mean_dd: float = 0.0
    fraction_hit_80: float = 0.0
    consistent: bool = False  # Hermes v3: p5 ≥ 82% and mean ≥ 87%
    plain_english: str = ""

    def to_dict(self) -> dict:
        return {
            "n_runs": self.n_runs,
            "mean_wr": self.mean_wr,
            "median_wr": self.median_wr,
            "p5_wr": self.p5_wr,
            "p95_wr": self.p95_wr,
            "mean_dd": self.mean_dd,
            "fraction_hit_80": self.fraction_hit_80,
            "consistent": self.consistent,
            "plain_english": self.plain_english,
            "win_rates": self.win_rates,
            "max_dds": self.max_dds,
        }


def run_monte_carlo(
    *,
    config: Optional[EnhancedMispriceConfig] = None,
    n_runs: Optional[int] = None,
    n_markets: Optional[int] = None,
    base_seed: int = 100,
    show_progress: bool = True,
) -> tuple[MonteCarloSummary, list[MetricsReport]]:
    cfg = config or load_enhanced_config()
    runs = int(n_runs or cfg.monte_carlo_runs)
    # Cap for CI friendliness unless user asks for more
    runs = max(10, runs)
    wrs: list[float] = []
    dds: list[float] = []
    ns: list[int] = []
    reports: list[MetricsReport] = []

    progress_ctx = Progress(
        SpinnerColumn(),
        TextColumn("[bold]Monte Carlo[/]"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) if show_progress else None

    def _one(i: int) -> MetricsReport:
        seed = base_seed + i * 97
        eng = BacktestEngine(cfg, mode="enhanced", seed=seed)
        # Fewer markets per MC run for speed; still enough for WR signal
        n = int(n_markets or min(4000, cfg.synthetic_n_markets))
        er = eng.run_synthetic(n_markets=n, seed=seed)
        return compute_metrics(er)

    if progress_ctx is not None:
        with progress_ctx as progress:
            task = progress.add_task("runs", total=runs)
            for i in range(runs):
                m = _one(i)
                reports.append(m)
                wrs.append(m.win_rate)
                dds.append(m.max_drawdown_pct)
                ns.append(m.n_trades)
                progress.advance(task)
    else:
        for i in range(runs):
            m = _one(i)
            reports.append(m)
            wrs.append(m.win_rate)
            dds.append(m.max_drawdown_pct)
            ns.append(m.n_trades)

    arr = np.asarray(wrs, dtype=float)
    p5 = float(np.percentile(arr, 5)) if len(arr) else 0.0
    from models.config import TARGET_MC_P5, TARGET_WR_MEAN

    mean_wr = float(arr.mean()) if len(arr) else 0.0
    consistent = p5 >= TARGET_MC_P5 and mean_wr >= TARGET_WR_MEAN
    summary = MonteCarloSummary(
        n_runs=runs,
        win_rates=wrs,
        max_dds=dds,
        n_trades=ns,
        mean_wr=mean_wr,
        median_wr=float(np.median(arr)) if len(arr) else 0.0,
        p5_wr=p5,
        p95_wr=float(np.percentile(arr, 95)) if len(arr) else 0.0,
        mean_dd=float(np.mean(dds)) if dds else 0.0,
        fraction_hit_80=float(np.mean(arr >= 0.80)) if len(arr) else 0.0,
        consistent=consistent,
        plain_english=(
            f"Across {runs} random universes, average win rate was {100 * mean_wr:.1f}% "
            f"(median {100 * float(np.median(arr)):.1f}%). "
            f"The unlucky 5th-percentile run still hit {100 * p5:.1f}% — "
            + (
                f"clears Hermes v3 gates (p5≥{100 * TARGET_MC_P5:.0f}%, mean≥{100 * TARGET_WR_MEAN:.0f}%)."
                if consistent
                else (
                    f"misses Hermes v3 MC gates (need p5≥{100 * TARGET_MC_P5:.0f}% and "
                    f"mean≥{100 * TARGET_WR_MEAN:.0f}%); tighten filters before trusting live paper."
                )
            )
        ),
    )
    logger.info(
        "MonteCarlo: mean_wr=%.1f%% p5=%.1f%% hit80=%.0f%% consistent=%s",
        100 * summary.mean_wr,
        100 * summary.p5_wr,
        100 * summary.fraction_hit_80,
        summary.consistent,
    )
    return summary, reports
