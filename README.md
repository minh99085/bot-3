# Financial Freedom Bot — Hermes v2

Autonomous Polymarket paper bot (BTC/ETH up-down, incl. 5m/15m) with **$2000 starting bankroll**, Loop Engineering cadence, Ruuj portfolio construction, Chainlink ground-truth, and a live Streamlit desk.

**Targets:** consistent 80%+ WR · DD &lt; 8% · PF &gt; 1.4 · EV after CLOB fees/slippage.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.

# Bot (paper)
python -m hermes.hermes_loop demo
python -m hermes.hermes_loop overnight

# Dashboard (separate terminal) — $2000 desk
streamlit run dashboard.py
```

---

## How pre-trade sizing drives 80%+ WR

Handoff is not “pick a notional.” After signals are generated:

1. **Portfolio weights** — Ledoit-Wolf cov → HRP / edge-RP → Black-Litterman views → cut/reduce caps  
2. **Pre-trade analysis** (`hermes/pretrade.py`) for each signal:
   - Sleeve WR / EV from the ledger  
   - Binding rules from `LESSONS.md`  
   - Live EV from **orderbook slip + Chainlink alignment**  
   - Portfolio impact (diversification / HHI)  
   - Output **% of $2000 bankroll** (max 3%) or **0% skip**  
3. **Verifier** approves **signal quality and proposed size** (rejects `pretrade_skip`)  
4. Decisions are logged to `data/paper/pretrade_decisions.jsonl` → visible on the dashboard  

Skipping toxic or low-EV tickets is how the loop protects win rate while lessons compound overnight.

```
Discovery → Signals → HRP/BL allocation → Pre-trade size% → Verifier → Paper fill
                                              ↓
                                    LESSONS + ledger → dashboard
```

---

## Dashboard

`dashboard.py` auto-refreshes every 8s and shows:

- Equity curve + total PnL from $2000  
- Open positions / exposure  
- Recent trades table  
- Sub-strategy cards (WR, EV, weight, trend)  
- Portfolio metrics (div ratio, HHI, CUT/REDUCE)  
- Latest lessons  
- Chainlink prices + alignment  
- Pre-trade sizing decisions  

---

## Architecture (5×6)

| Move | Module |
|------|--------|
| Discovery | `discovery.py` + hybrid Chainlink/CLOB |
| Handoff | `portfolio.py` + **`pretrade.py`** + worktrees |
| Verification | `verifier.py` (signal + size + oracle) |
| Persistence | `STATE.md` / `LESSONS.md` / ledgers |
| Scheduling | `@loop` / `@goal` in `hermes_loop.py` |

Connectors: `polymarket.py` (`py-clob-client-v2`), `chainlink.py`, `hybrid_data.py`, `broker.py`.

---

## Paper → live

1. Paper evidence: WR ≥ 80%, PF &gt; 1.4, DD &lt; 8%  
2. `CHAINLINK_API_KEY/SECRET` (optional; AggregatorV3 fallback works)  
3. `POLYMARKET_PK` + STATE `Live Enabled` + `HERMES_LIVE=1`  

Git: push **directly to `main`** (no feature branches).
