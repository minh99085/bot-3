"""Rich CLI for the production backtest suite.

Examples
--------
  python -m backtest run --synthetic --n_markets 8000 --seed 42 --plots
  python -m backtest monte-carlo --n_runs 100 --n_markets 4000
  python -m backtest tune --trials 30
  python -m backtest compare --n_markets 8000
  python -m backtest run --historical --csv data/backtest/example_historical.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backtest.artifacts import save_run_bundle
from backtest.compare import compare_naive_vs_enhanced
from backtest.engine import BacktestEngine, run_backtest
from backtest.metrics import (
    calibration_points,
    compute_metrics,
    threshold_sweep,
)
from backtest.monte_carlo import run_monte_carlo
from backtest.plots import (
    save_calibration,
    save_equity_and_drawdown,
    save_monte_carlo_hist,
    save_threshold_sweep,
)
from backtest.tuning import run_tuning
from models.config import load_enhanced_config

console = Console()
logger = logging.getLogger(__name__)


def _print_metrics_table(m) -> None:
    table = Table(title="Backtest metrics (plain English)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Win rate", f"{m.win_rate:.1%}")
    table.add_row("Trades taken", str(m.n_trades))
    table.add_row("Selectivity", f"{m.selectivity:.1%}")
    table.add_row("Profit factor", f"{m.profit_factor:.2f}")
    table.add_row("Max drawdown", f"{m.max_drawdown_pct:.1%}")
    table.add_row("Expectancy / trade", f"${m.expectancy_usd:.2f}")
    table.add_row("Model Brier", f"{m.brier:.3f}")
    table.add_row("Target met (≥80% WR, DD≤15%)", "YES ✓" if m.target_met else "NO ✗")
    console.print(table)
    console.print(Panel(m.plain_english, title="What this means"))


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_enhanced_config(args.config)
    if args.n_markets:
        cfg.synthetic_n_markets = int(args.n_markets)
    if args.seed is not None:
        cfg.synthetic_seed = int(args.seed)

    engine = BacktestEngine(cfg, mode="enhanced", seed=cfg.synthetic_seed)

    if args.historical:
        from backtest.historical import (
            load_historical_decisions,
            write_example_historical_csv,
        )

        if args.csv:
            decisions = load_historical_decisions(args.csv)
        else:
            write_example_historical_csv()
            decisions = load_historical_decisions()
        if len(decisions) < 20:
            console.print("[yellow]Few historical rows — falling back to synthetic.[/]")
            er = engine.run_synthetic(n_markets=args.n_markets, seed=args.seed)
        else:
            er = engine.run_on_decisions(decisions)
    else:
        console.print(
            f"[bold]Running synthetic backtest[/] n_markets={cfg.synthetic_n_markets} seed={cfg.synthetic_seed}"
        )
        er = engine.run_synthetic(n_markets=args.n_markets, seed=args.seed)

    m = compute_metrics(er)
    _print_metrics_table(m)
    console.print(m.summary_text())

    plot_paths = []
    run_extra = {
        "mode": er.mode,
        "n_markets": er.n_markets,
        "n_decision_points": er.n_decision_points,
        "seed": er.seed,
        "threshold_sweep": threshold_sweep(er.decisions),
        "calibration": calibration_points(er.decisions),
    }

    if args.plots:
        from backtest.artifacts import new_run_dir
        import json

        run_dir = new_run_dir("synthetic" if not args.historical else "historical")
        p1 = save_equity_and_drawdown(er.equity_curve, run_dir / "equity_drawdown.png")
        p2 = save_calibration(calibration_points(er.decisions), run_dir / "calibration.png")
        p3 = save_threshold_sweep(threshold_sweep(er.decisions), run_dir / "threshold_sweep.png")
        plot_paths = [p for p in (p1, p2, p3) if p]
        (run_dir / "metrics.json").write_text(json.dumps(m.to_dict(), indent=2))
        (run_dir / "report.txt").write_text(m.summary_text())
        (run_dir / "extra.json").write_text(json.dumps(run_extra, indent=2, default=str))
        (run_dir / "plots_index.json").write_text(
            json.dumps([str(p) for p in plot_paths], indent=2)
        )
        console.print(f"[green]Plots + reports → {run_dir}[/]")
    else:
        path = save_run_bundle(
            tag="synthetic" if not args.historical else "historical",
            metrics=m.to_dict(),
            summary_text=m.summary_text(),
            extra=run_extra,
        )
        console.print(f"[green]Reports → {path}[/]")

    return 0 if m.target_met else 1


def cmd_monte_carlo(args: argparse.Namespace) -> int:
    cfg = load_enhanced_config(args.config)
    summary, _ = run_monte_carlo(
        config=cfg,
        n_runs=args.n_runs or cfg.monte_carlo_runs,
        n_markets=args.n_markets or 4000,
        base_seed=args.seed or 100,
        show_progress=True,
    )
    console.print(Panel(summary.plain_english, title="Monte Carlo"))
    table = Table(title="WR distribution")
    table.add_column("Stat")
    table.add_column("Value", justify="right")
    table.add_row("Runs", str(summary.n_runs))
    table.add_row("Mean WR", f"{summary.mean_wr:.1%}")
    table.add_row("Median WR", f"{summary.median_wr:.1%}")
    table.add_row("5th percentile WR", f"{summary.p5_wr:.1%}")
    table.add_row("95th percentile WR", f"{summary.p95_wr:.1%}")
    table.add_row("% runs ≥80% WR", f"{summary.fraction_hit_80:.0%}")
    table.add_row("Consistent (p5≥75%)", "YES ✓" if summary.consistent else "NO ✗")
    console.print(table)

    from backtest.artifacts import new_run_dir

    run_dir = new_run_dir("monte_carlo")
    plot = None
    if args.plots:
        plot = save_monte_carlo_hist(summary.win_rates, run_dir / "wr_hist.png")
    (run_dir / "metrics.json").write_text(__import__("json").dumps(summary.to_dict(), indent=2))
    (run_dir / "report.txt").write_text(summary.plain_english)
    console.print(f"[green]Artifacts → {run_dir}[/]" + (f" plot={plot}" if plot else ""))
    return 0 if summary.consistent else 1


def cmd_tune(args: argparse.Namespace) -> int:
    cfg = load_enhanced_config(args.config)
    result = run_tuning(
        config=cfg,
        n_trials=args.trials or cfg.tune_trials,
        n_markets=args.n_markets or 5000,
        seed=args.seed or 42,
    )
    console.print(Panel(result.plain_english, title="Tuning result"))
    console.print(result.best_params)
    path = save_run_bundle(
        tag="tune",
        metrics=result.best_metrics,
        summary_text=result.plain_english + "\n" + str(result.best_params),
        extra=result.to_dict(),
    )
    console.print(f"[green]Artifacts → {path}[/]")
    return 0 if result.best_metrics.get("feasible") else 1


def cmd_compare(args: argparse.Namespace) -> int:
    cfg = load_enhanced_config(args.config)
    result = compare_naive_vs_enhanced(
        config=cfg,
        n_markets=args.n_markets or 8000,
        seed=args.seed or 42,
    )
    console.print(result.summary_text())
    path = save_run_bundle(
        tag="compare",
        metrics=result.to_dict(),
        summary_text=result.summary_text(),
    )
    console.print(f"[green]Artifacts → {path}[/]")
    return 0 if result.enhanced.target_met else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m backtest",
        description="Hermes enhanced-misprice backtest suite (validate 80%+ WR)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--config", default="config/enhanced_misprice.yaml")
    sub = p.add_subparsers(dest="cmd")

    # Legacy flat flags still work via default cmd=run when using old style
    run_p = sub.add_parser("run", help="Single synthetic/historical backtest")
    run_p.add_argument("--synthetic", action="store_true", default=True)
    run_p.add_argument("--historical", action="store_true")
    run_p.add_argument("--csv", type=str, default=None)
    run_p.add_argument("--n_markets", type=int, default=None)
    run_p.add_argument("--seed", type=int, default=None)
    run_p.add_argument("--plots", action="store_true")
    run_p.set_defaults(func=cmd_run)

    mc = sub.add_parser("monte-carlo", help="WR distribution across many seeds")
    mc.add_argument("--n_runs", type=int, default=None)
    mc.add_argument("--n_markets", type=int, default=4000)
    mc.add_argument("--seed", type=int, default=100)
    mc.add_argument("--plots", action="store_true")
    mc.set_defaults(func=cmd_monte_carlo)

    tune = sub.add_parser("tune", help="Search thresholds for robust 80%+ WR")
    tune.add_argument("--trials", type=int, default=None)
    tune.add_argument("--n_markets", type=int, default=5000)
    tune.add_argument("--seed", type=int, default=42)
    tune.set_defaults(func=cmd_tune)

    comp = sub.add_parser("compare", help="Naive misprice vs full enhanced stack")
    comp.add_argument("--n_markets", type=int, default=8000)
    comp.add_argument("--seed", type=int, default=42)
    comp.set_defaults(func=cmd_compare)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Backward compatible: `python -m backtest --synthetic --n_markets 8000`
    if argv and argv[0] not in (
        "run",
        "monte-carlo",
        "tune",
        "compare",
        "-h",
        "--help",
    ):
        argv = ["run"] + argv

    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
