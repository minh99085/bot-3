# VPS Full Backtest Report — 2026-07-15

Published from production VPS (`207.246.96.45`) for Grok / reviewer inspection.

## Reproduce

```bash
python -m backtest --n-markets 5000 --seed 42 --compare-baseline --no-rich
```

VPS (inside bot container):

```bash
cd /opt/financial-freedom-bot
docker compose exec bot python -m backtest --n-markets 5000 --seed 42 --compare-baseline --no-rich
```

## Verdict

**Target met:** 91.1% win rate on 866 trades | Monte Carlo 5th percentile: 86.8% | Max DD: 10.0%

| Metric | Value |
|--------|-------|
| Win rate | 91.1% |
| Trades taken | 866 / 15,000 decisions (5.8% selectivity) |
| Profit factor | 3.28 |
| Expectancy / trade | $20.40 |
| Total PnL | $17,665 (883% return on $2k bankroll) |
| Max drawdown | 10.0% |
| Model Brier | 0.143 |
| Monte Carlo (20 seeds) | mean 88.2%, p5 86.8%, all runs ≥80% |

## Naive vs Enhanced (same 5000 markets)

| Stack | Win rate | Max DD | Trades | Profit factor |
|-------|----------|--------|--------|---------------|
| Naive (edge-only, fixed size) | 56.3% | 14.9% | 3,288 | 4.52 |
| Enhanced (Beta + Kelly + risk budget) | 91.1% | 10.0% | 866 | 3.28 |

**WR lift:** +34.8 pp. Enhanced stack wins by skipping mid-odds / low-conviction bets naive trading still takes.

## Parameters used

See `parameters_used.yaml`. Key filters: `min_edge=0.12`, `min_conviction=0.95`, `kappa_base=0.35`, `risk_budget=0.20`.

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

- **By category:** crypto 90.6%, economics 92.0%, elections 88.6%, sports 93.5%
- **By edge:** 0.10–0.15 → 91.4%, 0.15+ → 91.0%
- **By days-to-resolution:** 0–5d 93.7%, 5–21d 89.3%, 21–60d 89.1%, 60d+ 94.5%

## Caveats for reviewers

1. **Synthetic universe** — not live Polymarket tape; validates strategy stack under calibrated noise (Brier ~0.14).
2. **High selectivity** — only 5.8% of decision points become trades; live fill rate may differ.
3. **Monte Carlo DD** — some individual seed runs exceed 15% DD (e.g. 21.6%); aggregate p5 WR still clears 80% target.
4. **Paper only** — `HERMES_PAPER_ONLY=1` on VPS; no real capital at risk.

## Source artifact path (VPS container)

`/app/artifacts/backtest_runs/20260715_161859/`
