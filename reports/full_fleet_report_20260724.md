# Bot-3 — Full fleet paper report

- **Generated (UTC):** 2026-07-24T02:31:27.605646+00:00
- **Host:** `207.246.96.45` (`/opt/financial-freedom-bot`)
- **Git HEAD at write:** see commit after push
- **Fleet:** 10 lanes · $2k each · $20k bankroll · BTC-15m + lane07 ETH-15m

## Fleet headline

| Metric | Value |
|--------|------:|
| Bankroll | $20,000 |
| Equity | $19,895.47 |
| **Fleet P&L** | **$-104.53** |
| Win rate | 56.4% |
| Settled trades | 101 |
| Wins / losses | 57 / 44 |
| Open positions | 0 |
| Lanes with data | 7 |

## Time windows (settlements)

| Window | n | W/L | WR | PnL |
|--------|--:|----:|---:|----:|
| all | 101 | 57/44 | 56.4% | $-104.53 |
| last_24h | 69 | 43/26 | 62.3% | $+116.42 |
| last_10h | 35 | 23/12 | 65.7% | $+150.61 |
| last_3h | 8 | 3/5 | 37.5% | $-79.98 |

## Per-lane scoreboard

| Lane | Asset | Filter | Variant | Role | Equity | PnL | Settled | W/L | WR | Status |
|------|-------|--------|---------|------|-------:|----:|--------:|----:|---:|--------|
| `lane01_baseline` | BTC | btc15 | baseline | control | $1,926.18 | $-73.82 | 8 | 3/5 | 38% | watching |
| `lane02_autonomy` | BTC | btc15 | autonomy | experiment | $2,054.57 | $+54.57 | 9 | 5/4 | 56% | watching |
| `lane03_drift` | BTC | btc15 | drift_barrier | experiment | $1,890.51 | $-109.49 | 13 | 7/6 | 54% | watching |
| `lane04_favcont70` | BTC | btc15 | fav_cont_70 | experiment | $2,000.00 | $+0.00 | 0 | 0/0 | — | idle |
| `lane05_favsniper` | BTC | btc15 | fav_sniper | experiment | $2,000.00 | $+0.00 | 0 | 0/0 | — | active |
| `lane06_garch` | BTC | btc15 | garch_sigma | experiment | $1,960.69 | $-39.31 | 14 | 5/9 | 36% | watching |
| `lane07_ethdrift` | ETH | eth15 | drift_barrier | experiment | $2,000.00 | $+0.00 | 0 | 0/0 | — | idle |
| `lane08_favdepth` | BTC | btc15 | fav_cont_depth | experiment | $2,021.28 | $+21.28 | 2 | 2/0 | 100% | watching |
| `lane09_random` | BTC | btc15 | random_null | null | $1,973.90 | $-26.10 | 48 | 28/20 | 58% | watching |
| `lane10_favopen` | BTC | btc15 | fav_cont_open | experiment | $2,068.34 | $+68.34 | 7 | 7/0 | 100% | watching |

## Paired scoreboard vs random null

- Null lane: `lane09_random`
- Shared BTC windows (paired): 0
- Note: **lane07 ETH** is unpaired vs BTC random by design.

| Lane | Asset | Role | n | WR | PnL | N paired | ΔPnL vs null |
|------|-------|------|--:|---:|----:|---------:|-------------:|
| `lane10_favopen` | BTC | experiment | 7 | 100% | $+68.34 | 4 | $+20.70 |
| `lane02_autonomy` | BTC | experiment | 9 | 56% | $+54.57 | 4 | $+9.31 |
| `lane08_favdepth` | BTC | experiment | 2 | 100% | $+21.28 | 0 | $+0.00 |
| `lane04_favcont70` | BTC | experiment | 0 | 0% | $+0.00 | 0 | $+0.00 |
| `lane05_favsniper` | BTC | experiment | 0 | 0% | $+0.00 | 0 | $+0.00 |
| `lane07_ethdrift` | ETH | experiment | 0 | 0% | $+0.00 | 0 | $+0.00 |
| `lane09_random` | BTC | null | 48 | 58% | $-26.10 | 0 | $+0.00 |
| `lane03_drift` | BTC | experiment | 13 | 54% | $-109.49 | 5 | $-82.79 |
| `lane01_baseline` | BTC | control | 8 | 38% | $-73.82 | 6 | $-143.82 |
| `lane06_garch` | BTC | experiment | 14 | 36% | $-39.31 | 11 | $-167.19 |

- lanes below 30 trades (noise): ['lane01_baseline', 'lane02_autonomy', 'lane03_drift', 'lane06_garch', 'lane08_favdepth', 'lane10_favopen']

## Ticket price buckets (all-time remaining ledger)

| Bucket | n | WR | PnL |
|--------|--:|---:|----:|
| Cheap ≤0.25 | 8 | 0% | $-228.12 |
| Mid | 72 | 53% | $+21.89 |
| Exp ≥0.75 | 21 | 90% | $+101.70 |

## Last 50 trades (newest first)

- Rows: 50 · Settled in view: 50 · Open in view: 0
- **Fleet P&L (single source of truth):** $-104.53

| # | Time UTC | Lane | Asset | Status | Dir | Size | Entry | Won | PnL | Slug |
|--:|----------|------|-------|--------|-----|-----:|------:|-----|----:|------|
| 1 | 2026-07-24 02:03:21 | `lane02_autonomy` | BTC | settled | UP | $40.00 | 0.6033 | False | $-40.00 | `btc-updown-15m-1784857500` |
| 2 | 2026-07-24 02:01:11 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5938 | True | $+27.36 | `btc-updown-15m-1784857500` |
| 3 | 2026-07-24 01:46:05 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5072 | False | $-40.00 | `btc-updown-15m-1784856600` |
| 4 | 2026-07-24 01:18:04 | `lane02_autonomy` | BTC | settled | UP | $40.00 | 0.4332 | True | $+52.33 | `btc-updown-15m-1784854800` |
| 5 | 2026-07-24 00:45:48 | `lane09_random` | BTC | settled | UP | $40.00 | 0.5366 | False | $-40.00 | `btc-updown-15m-1784853000` |
| 6 | 2026-07-24 00:32:48 | `lane02_autonomy` | BTC | settled | DOWN | $40.00 | 0.5462 | True | $+33.23 | `btc-updown-15m-1784852100` |
| 7 | 2026-07-24 00:30:44 | `lane09_random` | BTC | settled | UP | $40.00 | 0.5748 | False | $-40.00 | `btc-updown-15m-1784852100` |
| 8 | 2026-07-24 00:02:35 | `lane02_autonomy` | BTC | settled | UP | $32.90 | 0.3706 | False | $-32.90 | `btc-updown-15m-1784850300` |
| 9 | 2026-07-23 23:20:02 | `lane01_baseline` | BTC | settled | UP | $40.00 | 0.5174 | False | $-40.00 | `btc-updown-15m-1784847600` |
| 10 | 2026-07-23 23:15:21 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5366 | True | $+34.54 | `btc-updown-15m-1784847600` |
| 11 | 2026-07-23 23:00:16 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5462 | True | $+33.23 | `btc-updown-15m-1784846700` |
| 12 | 2026-07-23 22:47:17 | `lane02_autonomy` | BTC | settled | UP | $40.00 | 0.5174 | True | $+37.31 | `btc-updown-15m-1784845800` |
| 13 | 2026-07-23 22:34:58 | `lane03_drift` | BTC | settled | UP | $3.88 | 0.8700 | True | $+0.58 | `btc-updown-15m-1784844900` |
| 14 | 2026-07-23 22:19:29 | `lane01_baseline` | BTC | settled | UP | $40.00 | 0.3914 | False | $-40.00 | `btc-updown-15m-1784844000` |
| 15 | 2026-07-23 22:05:00 | `lane09_random` | BTC | settled | UP | $40.00 | 0.8100 | True | $+9.38 | `btc-updown-15m-1784843100` |
| 16 | 2026-07-23 22:04:20 | `lane01_baseline` | BTC | settled | UP | $40.00 | 0.7600 | True | $+12.63 | `btc-updown-15m-1784843100` |
| 17 | 2026-07-23 21:49:51 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784842200` |
| 18 | 2026-07-23 21:19:34 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784840400` |
| 19 | 2026-07-23 21:19:17 | `lane03_drift` | BTC | settled | UP | $40.00 | 0.5174 | False | $-40.00 | `btc-updown-15m-1784840400` |
| 20 | 2026-07-23 20:34:10 | `lane09_random` | BTC | settled | UP | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784837700` |
| 21 | 2026-07-23 20:34:02 | `lane06_garch` | BTC | settled | UP | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784837700` |
| 22 | 2026-07-23 20:33:59 | `lane10_favopen` | BTC | settled | UP | $40.00 | 0.8162 | True | $+9.00 | `btc-updown-15m-1784837700` |
| 23 | 2026-07-23 20:33:57 | `lane03_drift` | BTC | settled | UP | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784837700` |
| 24 | 2026-07-23 20:33:44 | `lane01_baseline` | BTC | settled | UP | $40.00 | 0.5072 | True | $+38.86 | `btc-updown-15m-1784837700` |
| 25 | 2026-07-23 20:31:42 | `lane02_autonomy` | BTC | settled | UP | $40.00 | 0.4860 | True | $+42.30 | `btc-updown-15m-1784837700` |
| 26 | 2026-07-23 19:33:45 | `lane09_random` | BTC | settled | UP | $40.00 | 0.6316 | True | $+23.33 | `btc-updown-15m-1784834100` |
| 27 | 2026-07-23 19:33:38 | `lane06_garch` | BTC | settled | DOWN | $40.00 | 0.4100 | False | $-40.00 | `btc-updown-15m-1784834100` |
| 28 | 2026-07-23 19:18:41 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5270 | True | $+35.90 | `btc-updown-15m-1784833200` |
| 29 | 2026-07-23 19:18:28 | `lane03_drift` | BTC | settled | UP | $40.00 | 0.7600 | False | $-40.00 | `btc-updown-15m-1784833200` |
| 30 | 2026-07-23 18:33:24 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.4800 | False | $-40.00 | `btc-updown-15m-1784830500` |
| 31 | 2026-07-23 18:03:15 | `lane09_random` | BTC | settled | UP | $40.00 | 0.4018 | False | $-40.00 | `btc-updown-15m-1784828700` |
| 32 | 2026-07-23 17:48:10 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.8000 | True | $+10.00 | `btc-updown-15m-1784827800` |
| 33 | 2026-07-23 17:48:03 | `lane10_favopen` | BTC | settled | DOWN | $40.00 | 0.7963 | True | $+10.24 | `btc-updown-15m-1784827800` |
| 34 | 2026-07-23 16:47:47 | `lane10_favopen` | BTC | settled | DOWN | $40.00 | 0.8063 | True | $+9.61 | `btc-updown-15m-1784824200` |
| 35 | 2026-07-23 16:47:45 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.8100 | True | $+9.38 | `btc-updown-15m-1784824200` |
| 36 | 2026-07-23 16:17:39 | `lane10_favopen` | BTC | settled | DOWN | $25.19 | 0.7762 | True | $+7.26 | `btc-updown-15m-1784822400` |
| 37 | 2026-07-23 16:17:36 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.7700 | True | $+11.95 | `btc-updown-15m-1784822400` |
| 38 | 2026-07-23 16:02:36 | `lane06_garch` | BTC | settled | UP | $40.00 | 0.3706 | True | $+67.95 | `btc-updown-15m-1784821500` |
| 39 | 2026-07-23 16:02:32 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.6410 | False | $-40.00 | `btc-updown-15m-1784821500` |
| 40 | 2026-07-23 15:47:32 | `lane06_garch` | BTC | settled | DOWN | $40.00 | 0.3800 | False | $-40.00 | `btc-updown-15m-1784820600` |
| 41 | 2026-07-23 15:47:27 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.3900 | False | $-40.00 | `btc-updown-15m-1784820600` |
| 42 | 2026-07-23 14:47:11 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.8300 | True | $+8.19 | `btc-updown-15m-1784817000` |
| 43 | 2026-07-23 14:32:18 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5366 | False | $-40.00 | `btc-updown-15m-1784816100` |
| 44 | 2026-07-23 14:32:11 | `lane10_favopen` | BTC | settled | UP | $40.00 | 0.8162 | True | $+9.00 | `btc-updown-15m-1784816100` |
| 45 | 2026-07-23 14:32:06 | `lane03_drift` | BTC | settled | DOWN | $40.00 | 0.5366 | False | $-40.00 | `btc-updown-15m-1784816100` |
| 46 | 2026-07-23 14:17:12 | `lane09_random` | BTC | settled | UP | $40.00 | 0.5366 | True | $+34.54 | `btc-updown-15m-1784815200` |
| 47 | 2026-07-23 13:50:00 | `lane02_autonomy` | BTC | settled | DOWN | $40.00 | 0.6200 | False | $-40.00 | `btc-updown-15m-1784813400` |
| 48 | 2026-07-23 13:24:45 | `lane02_autonomy` | BTC | settled | DOWN | $40.00 | 0.4860 | True | $+42.30 | `btc-updown-15m-1784811600` |
| 49 | 2026-07-23 13:04:19 | `lane09_random` | BTC | settled | DOWN | $40.00 | 0.5200 | False | $-40.00 | `btc-updown-15m-1784810700` |
| 50 | 2026-07-23 13:04:18 | `lane02_autonomy` | BTC | settled | DOWN | $40.00 | 0.4437 | False | $-40.00 | `btc-updown-15m-1784810700` |

## Hourly PnL (last 24h)

| Hour UTC | n | WR | PnL |
|----------|--:|---:|----:|
| 2026-07-23 03:00 | 5 | 80% | $+38.84 |
| 2026-07-23 05:00 | 2 | 0% | $-80.00 |
| 2026-07-23 06:00 | 1 | 0% | $-40.00 |
| 2026-07-23 07:00 | 2 | 100% | $+35.28 |
| 2026-07-23 08:00 | 1 | 100% | $+21.51 |
| 2026-07-23 09:00 | 3 | 67% | $+28.44 |
| 2026-07-23 10:00 | 2 | 100% | $+81.32 |
| 2026-07-23 11:00 | 1 | 100% | $+35.90 |
| 2026-07-23 12:00 | 2 | 50% | $-16.67 |
| 2026-07-23 13:00 | 4 | 25% | $-77.70 |
| 2026-07-23 14:00 | 5 | 60% | $-28.27 |
| 2026-07-23 15:00 | 2 | 0% | $-80.00 |
| 2026-07-23 16:00 | 6 | 83% | $+66.15 |
| 2026-07-23 17:00 | 2 | 100% | $+20.24 |
| 2026-07-23 18:00 | 2 | 0% | $-80.00 |
| 2026-07-23 19:00 | 4 | 50% | $-20.77 |
| 2026-07-23 20:00 | 6 | 100% | $+206.74 |
| 2026-07-23 21:00 | 3 | 67% | $+37.72 |
| 2026-07-23 22:00 | 5 | 80% | $+19.90 |
| 2026-07-23 23:00 | 3 | 67% | $+27.77 |
| 2026-07-24 00:00 | 4 | 25% | $-79.67 |
| 2026-07-24 01:00 | 2 | 50% | $+12.33 |
| 2026-07-24 02:00 | 2 | 50% | $-12.64 |

## ETH lane (lane07_ethdrift)

- Label: 07 Eth Drift
- Equity: $2,000.00
- PnL: $+0.00
- Settled: 0 · W/L 0/0
- Status: idle
- Last slug: `—`

## Runtime

- Dashboard metric: single **Fleet P&L** (no dual last-50 table PnL)
- Active markets: **btc15** (9 lanes) + **eth15** (lane07)

## Bottom line

1. Fleet P&L **$-104.53** on **101** settled trades (WR 56.4%).
2. Random null: PnL **$-26.10** — BTC strategy lanes should beat this.
3. ETH drift lane: **$+0.00** settled=0.


## Docker status at report time

```
NAMES                     STATUS
hermes-nginx              Up 13 hours (healthy)
hermes-dashboard          Up 13 hours (healthy)
hermes-lane05_favsniper   Up 13 hours (healthy)
hermes-lane07_ethdrift    Up 13 hours (healthy)
hermes-lane08_favdepth    Up 13 hours (healthy)
hermes-lane06_garch       Up 13 hours (healthy)
hermes-lane01_baseline    Up 13 hours (healthy)
hermes-lane03_drift       Up 13 hours (healthy)
hermes-lane04_favcont70   Up 13 hours (unhealthy)
hermes-lane09_random      Up 13 hours (healthy)
hermes-lane02_autonomy    Up 13 hours (healthy)
hermes-lane10_favopen     Up 13 hours (healthy)
```

- Git: `0b14827` fix(dashboard): ETH-15m lane07 ethdrift labels, market filter, asset column
