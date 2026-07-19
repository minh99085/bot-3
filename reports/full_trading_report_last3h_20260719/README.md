# Full Trading Report — last 3 hours (2026-07-19)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `2026-07-19T10:11:16.901660+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 5 |
| Window W/L | 2 / 3 |
| Window WR | 40.0% |
| Window PnL | $+1,274.19 |
| Fleet equity (lifetime) | $11,154.19 / $10,000 |
| Fleet lifetime PnL | $+1,154.19 |
| Commit at pull | `6e7f3b4` |

## Per instance (window)

| Instance | Settled | PnL | WR | Equity | Turns | Orders |
|----------|---------|-----|----|--------|-------|--------|
| btc5 | 1 | $-300.00 | 0.0% | $1,700.00 | 35 | 1 |
| btc15 | 0 | $+0.00 | n/a | $1,880.00 | 35 | 0 |
| eth5 | 0 | $+0.00 | n/a | $2,000.00 | 35 | 0 |
| sol5 | 0 | $+0.00 | n/a | $2,000.00 | 36 | 0 |
| rotator | 4 | $+1,574.19 | 50.0% | $3,574.19 | 33 | 4 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + instance stats |
| `trades.json` | Settled trades in the 3h window |
