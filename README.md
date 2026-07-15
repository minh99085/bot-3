# Financial Freedom Bot — Hermes v2

Autonomous Polymarket bot (BTC/ETH up-down incl. **5m/15m**) built on Loop Engineering + Roan self-improvement + Ruuj portfolio construction + **Chainlink oracle ground-truth**.

**Targets:** consistent 80%+ WR · DD &lt; 8% · PF &gt; 1.4 · positive EV after realistic CLOB slippage.

Triad that closes fragility → consistency: **Chainlink-augmented data + Verifier + Lessons + Portfolio allocation**.

---

## Architecture (5 moves × 6 parts)

| Move | Module | Data role |
|------|--------|-----------|
| Discovery | `discovery.py` + `hybrid_data.py` | Gamma markets + Chainlink regime |
| Handoff | `portfolio.py` + worktrees | HRP/BL sizing across sub-strategies |
| Verification | `verifier.py` | Signal + allocation + **oracle alignment** |
| Persistence | `knowledge/*`, ledger | STATE portfolio + LESSONS (alpha + alloc + data) |
| Scheduling | `hermes_loop.py` `@loop`/`@goal` | Overnight paper cadence |

| Connector | Responsibility |
|-----------|----------------|
| `connectors/polymarket.py` | Gamma discovery + **`py-clob-client-v2`** orderbook / VWAP |
| `connectors/chainlink.py` | Data Streams (HMAC) or AggregatorV3 RPC fallback |
| `connectors/hybrid_data.py` | Merge CLOB + oracle → alignment, regime, timeframe |
| `connectors/broker.py` | Paper: walk book + log Chainlink; Live: CLOB post |

Sub-strategy key: `market_series|mode|regime|hN|timeframe` (e.g. `btc_updown_5m|momentum|trending_down|h14|5m`).

---

## Why Chainlink strengthens 80%+ WR

1. **Ground truth** for BTC/ETH — Polymarket short-horizon markets resolve with Chainlink + Automation; verifying against the same oracle reduces data noise and spoofed CEX ticks.
2. **Regime detection** uses oracle returns (not just YES mid), cutting false signals in chop.
3. **Verifier gate**: reject when `oracle_alignment` is low or HF oracle is stale — fewer garbage fills.
4. **Paper realism**: fills walk the live CLOB; oracle price is logged beside every BTC/ETH fill for post-trade lessons.

---

## Quick start (paper)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add CHAINLINK_API_KEY/SECRET for Data Streams
export PYTHONPATH=.

python -m hermes.hermes_loop demo
python -m hermes.hermes_loop overnight
pytest -q
```

Without Chainlink API keys, Hermes uses **on-chain AggregatorV3** via `ETH_RPC_URL` (public RPC). Synthetic demo mode (`demo`) still exercises the full loop.

### Paper → live migration

1. Paper WR ≥ 80%, PF &gt; 1.4, DD &lt; 8% on settled verifier-pass trades  
2. Set Data Streams keys (recommended) + `POLYMARKET_PK`  
3. `Live Enabled: true` in STATE + `HERMES_LIVE=1`  
4. `./scripts/run_live.sh` — posts via `py-clob-client-v2`  

---

## One turn

```
Gamma markets → Hybrid enrich (CLOB book + Chainlink)
 → Signals → Portfolio handoff (LW/HRP/BL/cut)
 → Verifier (signal + size + oracle)
 → Paper executor (book VWAP + oracle log)
 → Lessons → ALPHA/SKILL (incl. oracle + allocation rules)
```

---

## Verifier gates

Bucket edge · live EV · regime/conviction · AVOID · entry quality · DD sizing · **allocation** · **Chainlink oracle alignment** · lane not CUT/GATED.

---

## Git

Commit and push **directly to `main`** — no feature branches.
