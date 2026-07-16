# VPS Full Backtest Report — 2026-07-16

Published from production VPS (`207.246.96.45`) after deploy of commit `a033169` (real `cex_implied_up` as q, moderate filter preset).

## Reproduce

```bash
python -m backtest --n-markets 5000 --seed 42 --compare-baseline --no-rich
```

VPS (inside bot container):

```bash
cd /opt/financial-freedom-bot
docker compose exec hermes-btc5 bash -c 'cd /app && PYTHONPATH=/app python -m backtest --n-markets 5000 --seed 42 --compare-baseline --no-rich'
```

## Verdict

**Target missed:** 58.1% win rate on 2,494 trades | Monte Carlo 5th percentile: 48.0% | Max DD: 12.4%

| Metric | Value |
|--------|-------|
| Win rate | 58.1% |
| Trades taken | 2,494 / 15,000 decisions (16.6% selectivity) |
| Profit factor | 4.72 |
| Expectancy / trade | $119.07 |
| Total PnL | $296,963 (synthetic compounding) |
| Max drawdown | 12.4% |
| Model Brier | 0.143 |
| Monte Carlo (20 seeds) | mean 59.2%, p5 48.0%, 0/20 runs ≥80% WR |

## Naive vs Enhanced (same 5000 markets)

| Stack | Win rate | Max DD | Trades | Profit factor |
|-------|----------|--------|--------|---------------|
| Naive (edge-only, fixed size) | 53.3% | 15.5% | 4,224 | 3.95 |
| Enhanced (Beta + Kelly + risk budget) | 58.1% | 12.4% | 2,494 | 4.72 |

**WR lift:** +4.8 pp. Enhanced stack is pickier but does **not** clear the 80% WR gate under current moderate + real-q config.

## Parameters used

See `parameters_used.yaml`. Key filters (`mode: moderate`):

- `min_edge: 0.085`
- `min_conviction: 0.88`
- `extreme_q_high: 0.80` / `extreme_q_low: 0.20`
- `kappa_base: 0.40`

## Context vs 2026-07-15 report

The prior VPS bundle (`full_backtest_vps_20260715`) hit **91.1% WR** under **strict** filters (`min_conviction: 0.95`, artificial q push toward extremes). This run reflects **moderate** live-paper gates and **removed artificial q pushing** — synthetic WR drops because mid-odds trades are no longer inflated by fake extreme probabilities.

## Files in this bundle

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary (start here) |
| `report.json` | Full structured report + Monte Carlo + compare |
| `metrics.json` | Core metrics only |
| `extra.json` | Threshold sweep, calibration bins, MC per-seed WR/DD |
| `parameters_used.yaml` | Config snapshot for this run |
| `plots_index.json` | Plot filenames |
| `equity_drawdown.png` | Equity curve + drawdown |
| `wr_hist.png` | Win-rate distribution |
| `calibration.png` | Model calibration curve |
| `threshold_sweep.png` | WR vs min_conviction sweep |

## Win rate breakdown (enhanced)

- **By edge:** 0.06–0.10 → 41.4%, 0.10–0.15 → 50.0%, 0.15+ → 75.2%
- **By category:** crypto 55.8%, economics 59.9%, elections 57.8%, sports 59.0%

## Caveats for reviewers

1. **Synthetic universe** — not live Polymarket tape; validates strategy stack under calibrated noise (Brier ~0.14).
2. **Moderate + real q** — wider gates admit more mid-odds trades; WR on synthetic is ~58%, not 80%+.
3. **Monte Carlo** — 0/20 seeds hit 80% WR; p5 WR 48% — not production-ready on synthetic alone.
4. **Paper only** — `HERMES_PAPER_ONLY=1` on VPS; no real capital at risk.

## Source artifact path (VPS container)

`/app/artifacts/backtest_runs/20260716_024525/`
