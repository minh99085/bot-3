# Full Trading Report — last 5 hours (2026-07-19)

Pulled from VPS paper fleet (`207.246.96.45`). Window: settlements with `settled_at` ≥ `2026-07-18T22:50:12.149095+00:00`.

## Summary

| Metric | Value |
|--------|-------|
| Window settled | 5 |
| Window W/L | 3 / 2 |
| Window WR | 60.0% |
| Window PnL | $+3,095.24 |
| Fleet equity (lifetime) | $12,828.57 / $10,000 |
| Fleet lifetime PnL | $+2,828.57 |
| Commit at pull | `2bf92d8` |

## Per instance (window)

| Instance | Settled | PnL | WR | Equity |
|----------|---------|-----|----|--------|
| btc5 | 0 | $+0.00 | n/a | $2,273.33 |
| btc15 | 0 | $+0.00 | n/a | $1,880.00 |
| eth5 | 0 | $+0.00 | n/a | $2,000.00 |
| sol5 | 0 | $+0.00 | n/a | $2,000.00 |
| rotator | 5 | $+3,095.24 | 60.0% | $4,675.24 |

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Fleet + instance stats |
| `trades.json` | Settled trades in the 5h window |
