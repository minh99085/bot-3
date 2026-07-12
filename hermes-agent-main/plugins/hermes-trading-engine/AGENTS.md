# Hermes Trading Engine — Bot 3 Directional

Focused **BTC/ETH directional paper** engine (1h + 15m up/down). Loop Engineering lanes
(Discovery / Execution / Ledger). TradingView observe/context. Grok shadow. PAPER ONLY.

## Operator rules (ALWAYS)

- Repo: `https://github.com/minh99085/bot-3-clone-of-bot-1-` — commit on **`main` only** (no feature branches/PRs).
- After every push: `./scripts/sync-vps-bot3.sh` (or `.\scripts\sync-vps-bot3.ps1`) →
  `down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`.
- VPS: `root@207.246.96.45` `/opt/Bot-3` — dashboard http://207.246.96.45/dashboard
- Policy: `.grok/rules/bot3-deploy-policy.md`

## Architecture locks

- Loop Engineering: `.grok/rules/loop-engineering-lock.md`
- Cross-horizon learner: `.grok/rules/cross-horizon-learn-lock.md`
- Retained invariants: `scripts/pulse-babysit/frozen-env-keys.json` (PAPER ONLY, honest accounting)

## Env source of truth

`scripts/apply-loop-arch-env.py` + `scripts/setup-vps-training-env.py`

- Directional ON; arb / dep-arb execution OFF
- TV signal gate OFF (observe/context/tier only)
- Dashboard label: `Bot 3 Directional`

## Containers

- `hermes-training` — trading loop (`scripts/run_btc_pulse.py`)
- `hermes-trading-engine` — API + dashboard + TV webhook proxy on :80

Rebuild **both** after every deploy. Never rebuild only the API container.

## Local training (laptop)

```powershell
.\scripts\run-bot3-local-training.ps1
```

Dashboard: http://localhost:8810/dashboard
