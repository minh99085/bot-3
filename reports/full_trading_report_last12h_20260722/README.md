# Full Trading Report — last 12 hours (2026-07-22)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `2026-07-21T16:41:39.582634+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 9 |
| Window W/L | 6 / 3 |
| Window WR | 66.7% |
| Window PnL | $+68.83 |
| Fleet equity (lifetime) | $20,890.62 / $20,000 |
| Fleet lifetime PnL | $+890.62 |
| Commit at pull | `f922fdc` |

## Per lane (window)

| Lane | Settled | PnL | WR | Equity | Turns | Orders |
|------|---------|-----|----|--------|-------|--------|
| lane01_baseline | 0 | $+0.00 | n/a | $1,754.31 | 143 | 0 |
| lane02_chainlink | 0 | $+0.00 | n/a | $1,683.01 | 143 | 0 |
| lane03_favorite | 5 | $+4.44 | 80.0% | $2,004.44 | 143 | 5 |
| lane04_longshot | 1 | $-40.00 | 0.0% | $2,245.10 | 143 | 1 |
| lane05_late | 2 | $+144.39 | 100.0% | $2,214.67 | 143 | 2 |
| lane06_garch | 0 | $+0.00 | n/a | $2,137.70 | 143 | 0 |
| lane07_marketsigma | 0 | $+0.00 | n/a | $2,259.10 | 143 | 0 |
| lane08_legacy | 0 | $+0.00 | n/a | $2,044.92 | 143 | 0 |
| lane09_random | 0 | $+0.00 | n/a | $2,299.84 | 0 | 0 |
| lane10_depth | 1 | $-40.00 | 0.0% | $2,247.53 | 143 | 1 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + lane stats |
| `trades.json` | Settled trades in the last 12 hours window |

