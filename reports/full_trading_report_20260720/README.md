# Full Trading Report — lifetime (2026-07-20)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `1970-01-01T00:00:00+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 36 |
| Window W/L | 16 / 20 |
| Window WR | 44.4% |
| Window PnL | $+611.68 |
| Fleet equity (lifetime) | $20,611.68 / $20,000 |
| Fleet lifetime PnL | $+611.68 |
| Commit at pull | `39c4e2e` |

## Per lane (window)

| Lane | Settled | PnL | WR | Equity | Turns | Orders |
|------|---------|-----|----|--------|-------|--------|
| lane01_baseline | 4 | $-240.00 | 0.0% | $1,760.00 | 31 | 4 |
| lane02_chainlink | 5 | $-267.27 | 20.0% | $1,732.73 | 167 | 5 |
| lane03_favorite | 0 | $+0.00 | n/a | $2,000.00 | 168 | 0 |
| lane04_longshot | 4 | $+200.71 | 50.0% | $2,200.71 | 168 | 4 |
| lane05_late | 0 | $+0.00 | n/a | $2,000.00 | 168 | 0 |
| lane06_garch | 6 | $+75.40 | 33.3% | $2,075.40 | 167 | 6 |
| lane07_marketsigma | 0 | $+0.00 | n/a | $2,000.00 | 168 | 0 |
| lane08_legacy | 4 | $+151.01 | 50.0% | $2,151.01 | 168 | 4 |
| lane09_random | 9 | $+498.21 | 77.8% | $2,498.21 | 167 | 9 |
| lane10_depth | 4 | $+193.62 | 50.0% | $2,193.62 | 167 | 4 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + lane stats |
| `trades.json` | Settled trades in the lifetime window |

