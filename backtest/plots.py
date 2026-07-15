"""Matplotlib / seaborn plots for backtest artifacts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)


def _setup_style() -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_theme(style="whitegrid", context="talk")
        plt.rcParams["figure.figsize"] = (10, 5)
        plt.rcParams["figure.dpi"] = 120
    except Exception as exc:  # noqa: BLE001
        logger.warning("plot style setup failed: %s", exc)


def save_equity_and_drawdown(
    equity: Sequence[float],
    out_path: Path,
    *,
    title: str = "Equity curve & underwater drawdown",
) -> Optional[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed — skip equity plot")
        return None
    _setup_style()
    eq = np.asarray(equity, dtype=float)
    if len(eq) < 2:
        return None
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / np.maximum(peak, 1e-9)

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(eq, color="#0B6E4F", lw=2)
    ax1.set_ylabel("Equity ($)")
    ax1.set_title(title)
    ax2.fill_between(range(len(dd)), -dd * 100, 0, color="#C44536", alpha=0.7)
    ax2.set_ylabel("Drawdown %")
    ax2.set_xlabel("Event index")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_calibration(
    points: Sequence[tuple[float, float, int]],
    out_path: Path,
    *,
    title: str = "Calibration (reliability diagram)",
) -> Optional[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    _setup_style()
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ns = [p[2] for p in points]
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    ax.scatter(xs, ys, s=[max(20, n / 5) for n in ns], c="#1B4965", label="Model q bins")
    ax.set_xlabel("Predicted probability q (bin mid)")
    ax.set_ylabel("Observed win frequency")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_threshold_sweep(
    rows: Sequence[dict],
    out_path: Path,
    *,
    title: str = "Win rate vs min_conviction threshold",
) -> Optional[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    _setup_style()
    if not rows:
        return None
    xs = [r["min_conviction"] for r in rows]
    ys = [100 * r["win_rate"] for r in rows]
    fig, ax = plt.subplots()
    ax.plot(xs, ys, marker="o", color="#5C4B51")
    ax.axhline(80, color="#0B6E4F", ls="--", label="80% target")
    ax.axhline(82, color="#3D5A80", ls=":", label="82% stretch")
    ax.axhline(85, color="#EE6C4D", ls=":", label="85% stretch")
    ax.set_xlabel("min_conviction")
    ax.set_ylabel("Win rate %")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_monte_carlo_hist(
    win_rates: Sequence[float],
    out_path: Path,
    *,
    title: str = "Monte Carlo win-rate distribution",
) -> Optional[Path]:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        return None
    _setup_style()
    wr = np.asarray(win_rates, dtype=float) * 100
    fig, ax = plt.subplots()
    sns.histplot(wr, bins=20, kde=True, ax=ax, color="#1B4965")
    ax.axvline(80, color="#0B6E4F", ls="--", label="80% target")
    p5 = float(np.percentile(wr, 5))
    ax.axvline(p5, color="#C44536", ls=":", label=f"5th pct={p5:.1f}%")
    ax.set_xlabel("Win rate %")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
