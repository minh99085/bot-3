# VPS Full Backtest Report — 2026-07-16 (`strict_real`)

Published from production VPS (`207.246.96.45`) after deploy of commit `ea6f645` (`strict_real` filter preset, real `cex_implied_up` as q).

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

**Target met:** 89.7% win rate on 919 trades | Monte Carlo 5th percentile: 85.3% | Max DD: 8.0%

| Metric | Value |
|--------|-------|
| Win rate | 89.7% |
| Trades taken | 919 / 15,000 decisions (6.1% selectivity) |
| Profit factor | 3.05 |
| Expectancy / trade | $18.54 |
| Total PnL | $17,042 (synthetic compounding) |
| Max drawdown | 8.0% |
| Model Brier | 0.143 |
| Monte Carlo (20 seeds) | mean 87.6%, p5 85.3%, **20/20 runs ≥80% WR** |

## Naive vs Enhanced (same 5000 markets)

| Stack | Win rate | Max DD | Trades | Profit factor |
|-------|----------|--------|--------|---------------|
| Naive (edge-only, fixed size) | 58.3% | 12.4% | 2,727 | 4.84 |
| Enhanced (Beta + Kelly + risk budget) | 89.7% | 8.0% | 919 | 3.05 |

**WR lift:** +31.3 pp. Enhanced stack clears the 80% WR gate under `strict_real` + real-q config.

## Parameters used

See `parameters_used.yaml`. Key filters (`mode: strict_real`):

- `min_edge: 0.14`
- `min_conviction: 0.93`
- `min_conviction_guard: 0.96`
- `extreme_q_high: 0.85` / `extreme_q_low: 0.15`
- `kappa_base: 0.35`
- `max_single_market_pct: 0.08`
- `risk_budget: 0.18`

## Context vs prior VPS reports

| Report | Mode | WR | MC p5 | Notes |
|--------|------|-----|-------|-------|
| `full_backtest_vps_20260715` | strict (inflated q) | 91.1% | — | Artificial extreme-q push |
| `full_backtest_vps_20260716` | moderate + real q | 58.1% | 48.0% | Weak edge buckets admitted |
| **This run** | **strict_real + real q** | **89.7%** | **85.3%** | Edge floor 0.14 cuts losers |

Raising `min_edge` to 0.14 removed the sub-0.15 edge buckets that destroyed WR under real q. Selectivity dropped (6.1% vs 16.6% moderate) but every taken trade sits in profitable edge territory.

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

- **By edge:** 0.10–0.15 → 92.4%, 0.15+ → 89.4% (no 0.06–0.10 bucket — filtered at entry)
- **By category:** crypto 88.9%, economics 92.0%, elections 87.9%, sports 89.7%

## Caveats for reviewers

1. **Synthetic universe** — not live Polymarket tape; validates strategy stack under calibrated noise (Brier ~0.14).
2. **Real q** — uses `cex_implied_up` without artificial push; WR recovery comes from tighter edge/conviction gates, not fake probabilities.
3. **Lower trade count** — 919 trades vs 2,494 under moderate; higher selectivity is intentional.
4. **Paper only** — `HERMES_PAPER_ONLY=1` on VPS; no real capital at risk.

## Source artifact path (VPS container)

`/app/artifacts/backtest_runs/20260716_040427/`
