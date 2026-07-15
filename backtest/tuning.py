"""Parameter tuning — grid / random search for robust 80%+ WR configs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from backtest.engine import BacktestEngine
from backtest.metrics import compute_metrics
from models.config import EnhancedMispriceConfig, load_enhanced_config

logger = logging.getLogger(__name__)


@dataclass
class TuneResult:
    best_params: dict[str, Any]
    best_score: float
    best_metrics: dict[str, Any]
    trials: list[dict[str, Any]]
    plain_english: str

    def to_dict(self) -> dict:
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "best_metrics": self.best_metrics,
            "trials": self.trials,
            "plain_english": self.plain_english,
        }


def _score(wr: float, mdd: float, total_return: float) -> float:
    """Composite: win_rate * (1 - max_dd) * log(1 + total_return).

    Hard constraints applied by caller (return -inf if violated).
    """
    return float(wr * (1.0 - mdd) * np.log1p(max(0.0, total_return)))


def run_tuning(
    *,
    config: Optional[EnhancedMispriceConfig] = None,
    n_trials: Optional[int] = None,
    n_markets: int = 5000,
    seed: int = 42,
    show_progress: bool = True,
) -> TuneResult:
    base = config or load_enhanced_config()
    trials_n = int(n_trials or base.tune_trials)
    rng = np.random.default_rng(seed)

    grid = {
        "min_edge": [0.08, 0.10, 0.12, 0.14],
        "min_conviction": [0.92, 0.94, 0.95, 0.96, 0.97],
        "kappa_base": [0.20, 0.25, 0.30, 0.35],
        "risk_budget": [0.12, 0.16, 0.20],
        "n_eff_crypto": [60, 80, 100, 120],
        "extreme_q_high": [0.82, 0.86, 0.88],
    }

    trials: list[dict[str, Any]] = []
    best_score = -1e18
    best_params: dict[str, Any] = {}
    best_metrics: dict[str, Any] = {}

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]Tuning[/]"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) if show_progress else None

    def _eval(params: dict[str, Any]) -> dict[str, Any]:
        cfg = base.model_copy(deep=True)
        cfg.min_edge = float(params["min_edge"])
        cfg.min_conviction = float(params["min_conviction"])
        cfg.kappa_base = float(params["kappa_base"])
        cfg.risk_budget = float(params["risk_budget"])
        cfg.n_eff.crypto = float(params["n_eff_crypto"])
        cfg.extreme_q_high = float(params["extreme_q_high"])
        cfg.extreme_q_low = float(min(0.20, 1.0 - cfg.extreme_q_high))
        cfg.synthetic_seed = seed
        eng = BacktestEngine(cfg, mode="enhanced", seed=seed)
        er = eng.run_synthetic(n_markets=n_markets, seed=seed)
        m = compute_metrics(er)
        feasible = m.win_rate >= 0.80 and m.max_drawdown_pct <= 0.15 and m.n_trades >= 25
        sc = _score(m.win_rate, m.max_drawdown_pct, m.total_return) if feasible else -1e9
        return {
            "params": params,
            "score": sc,
            "feasible": feasible,
            "win_rate": m.win_rate,
            "max_drawdown_pct": m.max_drawdown_pct,
            "total_return": m.total_return,
            "n_trades": m.n_trades,
            "brier": m.brier,
        }

    # Mix: evaluate a few grid corners + random samples
    corners = [
        {
            "min_edge": 0.12,
            "min_conviction": 0.95,
            "kappa_base": 0.35,
            "risk_budget": 0.20,
            "n_eff_crypto": 80,
            "extreme_q_high": 0.86,
        },
        {
            "min_edge": 0.14,
            "min_conviction": 0.97,
            "kappa_base": 0.25,
            "risk_budget": 0.16,
            "n_eff_crypto": 100,
            "extreme_q_high": 0.88,
        },
    ]
    samples = list(corners)
    while len(samples) < trials_n:
        samples.append(
            {
                "min_edge": float(rng.choice(grid["min_edge"])),
                "min_conviction": float(rng.choice(grid["min_conviction"])),
                "kappa_base": float(rng.choice(grid["kappa_base"])),
                "risk_budget": float(rng.choice(grid["risk_budget"])),
                "n_eff_crypto": float(rng.choice(grid["n_eff_crypto"])),
                "extreme_q_high": float(rng.choice(grid["extreme_q_high"])),
            }
        )

    def _run_all() -> None:
        nonlocal best_score, best_params, best_metrics
        for params in samples:
            row = _eval(params)
            trials.append(row)
            if row["score"] > best_score:
                best_score = row["score"]
                best_params = dict(params)
                best_metrics = {
                    k: row[k]
                    for k in (
                        "win_rate",
                        "max_drawdown_pct",
                        "total_return",
                        "n_trades",
                        "brier",
                        "feasible",
                    )
                }

    if progress is not None:
        with progress as p:
            task = p.add_task("trials", total=len(samples))
            for params in samples:
                row = _eval(params)
                trials.append(row)
                if row["score"] > best_score:
                    best_score = row["score"]
                    best_params = dict(params)
                    best_metrics = {
                        k: row[k]
                        for k in (
                            "win_rate",
                            "max_drawdown_pct",
                            "total_return",
                            "n_trades",
                            "brier",
                            "feasible",
                        )
                    }
                p.advance(task)
    else:
        _run_all()

    plain = (
        f"Best feasible config: {best_params}. "
        f"Win rate={100 * best_metrics.get('win_rate', 0):.1f}%, "
        f"max DD={100 * best_metrics.get('max_drawdown_pct', 0):.1f}%, "
        f"return={100 * best_metrics.get('total_return', 0):.1f}%. "
        "Copy these into config/enhanced_misprice.yaml to lock them in."
        if best_metrics.get("feasible")
        else "No trial cleared WR≥80% and DD≤15%. Increase n_markets or tighten extremes."
    )
    logger.info("Tuning best_score=%.4f params=%s", best_score, best_params)
    return TuneResult(
        best_params=best_params,
        best_score=best_score,
        best_metrics=best_metrics,
        trials=trials,
        plain_english=plain,
    )
