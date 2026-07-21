# Full Trading Report — last 3 hours (2026-07-21)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `2026-07-21T15:45:52.995034+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 0 |
| Window W/L | 0 / 0 |
| Window WR | n/a |
| Window PnL | $+0.00 |
| Fleet equity (lifetime) | $20,821.79 / $20,000 |
| Fleet lifetime PnL | $+821.79 |
| Commit at pull | `d5d0387` |

## Per lane (window)

| Lane | Settled | PnL | WR | Equity | Turns | Orders |
|------|---------|-----|----|--------|-------|--------|
| lane01_baseline | 0 | $+0.00 | n/a | $1,754.31 | 36 | 0 |
| lane02_chainlink | 0 | $+0.00 | n/a | $1,683.01 | 36 | 0 |
| lane03_favorite | 0 | $+0.00 | n/a | $2,000.00 | 36 | 0 |
| lane04_longshot | 0 | $+0.00 | n/a | $2,285.10 | 36 | 0 |
| lane05_late | 0 | $+0.00 | n/a | $2,070.28 | 36 | 0 |
| lane06_garch | 0 | $+0.00 | n/a | $2,137.70 | 36 | 0 |
| lane07_marketsigma | 0 | $+0.00 | n/a | $2,259.10 | 36 | 0 |
| lane08_legacy | 0 | $+0.00 | n/a | $2,044.92 | 36 | 0 |
| lane09_random | 0 | $+0.00 | n/a | $2,299.84 | 0 | 0 |
| lane10_depth | 0 | $+0.00 | n/a | $2,287.53 | 36 | 0 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + lane stats |
| `trades.json` | Settled trades in the last 3 hours window |

