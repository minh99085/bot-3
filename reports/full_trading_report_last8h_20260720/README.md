# Full Trading Report — last 8 hours (2026-07-20)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `2026-07-20T05:21:52.728851+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 0 |
| Window W/L | 0 / 0 |
| Window WR | n/a |
| Window PnL | $+0.00 |
| Fleet equity (lifetime) | $20,611.68 / $20,000 |
| Fleet lifetime PnL | $+611.68 |
| Commit at pull | `e4f9f2d` |

## Per lane (window)

| Lane | Settled | PnL | WR | Equity | Turns | Orders |
|------|---------|-----|----|--------|-------|--------|
| lane01_baseline | 0 | $+0.00 | n/a | $1,760.00 | 0 | 0 |
| lane02_chainlink | 0 | $+0.00 | n/a | $1,732.73 | 90 | 0 |
| lane03_favorite | 0 | $+0.00 | n/a | $2,000.00 | 91 | 0 |
| lane04_longshot | 0 | $+0.00 | n/a | $2,200.71 | 91 | 0 |
| lane05_late | 0 | $+0.00 | n/a | $2,000.00 | 91 | 0 |
| lane06_garch | 0 | $+0.00 | n/a | $2,075.40 | 91 | 0 |
| lane07_marketsigma | 0 | $+0.00 | n/a | $2,000.00 | 91 | 0 |
| lane08_legacy | 0 | $+0.00 | n/a | $2,151.01 | 91 | 0 |
| lane09_random | 0 | $+0.00 | n/a | $2,498.21 | 91 | 0 |
| lane10_depth | 0 | $+0.00 | n/a | $2,193.62 | 91 | 0 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + lane stats |
| `trades.json` | Settled trades in the last 8 hours window |

