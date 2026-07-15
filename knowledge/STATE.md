# STATE.md — Hermes Runtime Memory

> Capital, positions, performance, **portfolio metrics**, regime, pause flags.
> Updated every turn. The agent forgets; this file does not.

## Current Snapshot

- **Mode**: paper
- **Live Enabled**: false
- **Paper Only Lock**: true
- **Starting Bankroll USD**: 2000
- **Capital USD**: 2000
- **Open Exposure USD**: 0
- **Daily PnL USD**: 0
- **Max Drawdown Pct**: 0.0
- **Rolling WR (20)**: —
- **Rolling PF (20)**: —
- **Consecutive Losses**: 0
- **Circuit Breaker**: clear
- **Pause Loop**: false
- **Pause Reason**: none
- **Down Bias**: 0.35
- **Regime State**: unknown
- **Diversification Ratio**: 1.000
- **Concentration HHI**: 0.000
- **Substrategies Active**: 0
- **Substrategies Cut**: 0
- **Substrategies Reduce**: 0
- **Allocation Method**: none
- **Oracle BTC**: —
- **Oracle ETH**: —
- **Oracle Source**: none
- **Last Turn**: none
- **Last Turn At**: never
- **Last Turn Summary**: boot
- **Last Lessons Applied**: none

## Portfolio Sleeves

_Empty at boot — populated as sub-strategies settle._

| Sub-strategy | Action | Weight Cap | Rolling EV | WR | Confidence |
|--------------|--------|------------|------------|----|------------|
| — | — | — | — | — | — |

## Open Positions

_None — paper book empty at boot ($2000 USDC)._

## Recent Performance

| Window | WR | PF | n | Notes |
|--------|----|----|---|-------|
| Last 20 | — | — | 0 | cold start |
| Last 100 | — | — | 0 | cold start |
| Lifetime paper | — | — | 0 | cold start |

## Lane Status

| Lane | Status |
|------|--------|
| mean_reversion | active |
| momentum | active |
| liquidity_sweep | active |
| news_shock | paper_only |
| grok_signal | paper_only |
| tv_signal | paper_only |
| osmani_lane | gated |

## Goals in Flight

- Specialize on **BTC Up/Down 5m + 15m only** (preferred: `btc-updown-5m-1784113500`, `btc-updown-15m-1784113200`).
- Grow $2000 paper bankroll via verifier-pass + lessons-driven sizing toward 80%+ WR on these two series.
- Cold-start size 0.5% bankroll; scale only when lessons show positive EV + rising WR.

## Notes

**Market scope lock:** ONLY `btc-updown-5m-*` and `btc-updown-15m-*`. All other Polymarket events ignored.
Starting paper bankroll: **$2000 USDC**. Dashboard: http://&lt;IP&gt;/dashboard
