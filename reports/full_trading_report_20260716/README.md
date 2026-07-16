# Full Trading Report — 2026-07-16

Published from VPS paper fleet pull + bundled `strict_real` backtest validation.

## Reproduce

```bash
# Pull latest ledgers from VPS
python scripts/generate_trading_report.py --pull

# Or use existing local pull
python scripts/generate_trading_report.py --paper-dir data/paper_pull
```

## A) Live VPS paper fleet

| Metric | Value |
|--------|-------|
| Fleet bankroll | $10,000 (5 × $2k) |
| Fleet equity | $9,580.00 |
| Fleet PnL | $-420.00 |
| Settled trades | 7 |
| Win rate | 0.0% |
| Active instances | 3/5 |

Per-instance breakdown in `fleet_paper.json` and `trades.json`.

**Note:** Early post-reset sample — live crypto up/down lanes only (btc5, btc15, rotator). eth5/sol5 watching, no fills yet.

## B) Synthetic backtest (`strict_real`)

Source bundle: `reports/full_backtest_vps_20260716_strict_real`

| Metric | Value |
|--------|-------|
| Win rate | 89.7% |
| Trades | 919 / 15000 decisions |
| Selectivity | 6.1% |
| Profit factor | 3.05 |
| Max drawdown | 8.0% |
| Brier | 0.143 |
| Target met | True |

✅ Target met: 89.7% win rate on 919 trades | Monte Carlo 5th percentile: 85.3% | Max DD: 8.0%

## C) Deploy context

- **Commit:** `d5ac802`
- **VPS:** `207.246.96.45`
- **Mode:** `strict_real`, `HERMES_PAPER_ONLY=1`, `live_real_q=True`
- **Dashboard:** Bot 3
- **Autonomy stack:** MCHB, EHO, CBPF, RASP, RGMC, registry, ingest, continuous loop

Frozen gates: `min_edge=0.14`, `min_conviction=0.93`, κ=0.35, `max_single=0.08`, `risk_budget=0.18`.

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Per-instance fleet stats |
| `trades.json` | All settled trades with meta |
| `metrics.json` | Backtest metrics snapshot |
| `parameters_used.yaml` | strict_real config snapshot |

