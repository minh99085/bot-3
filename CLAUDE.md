# Operating mode for this agent (Bot 3)

Read at session start. Full deploy policy: `.grok/rules/bot3-deploy-policy.md`.

## Mandate
Act autonomously for Bot 3 (`bot-3-clone-of-bot-1-`). Commit on `main`, push, sync VPS, rebuild.
Do not create feature branches or PRs.

## Non-negotiables
1. NEVER fake or inflate performance.
2. Respect architecture locks (loop engineering, cross-horizon learner) unless overridden in the current message.
3. PAPER ONLY — no live trading.
4. Job incomplete until VPS `down --remove-orphans` → `build` → `up --force-recreate --remove-orphans` finishes.

## Deploy pipeline
1. Commit on `main`
2. `git push origin main`
3. `./scripts/sync-vps-bot3.sh` (or `.\scripts\sync-vps-bot3.ps1`)
4. Verify VPS HEAD == `origin/main`, containers healthy

VPS: `root@207.246.96.45` `/opt/Bot-3`  
Dashboard: http://207.246.96.45/dashboard (`Bot 3 Directional`)  
SSH key (cloud): `~/.ssh/bot3_cloud_agent` or secret `BOT3_VPS_SSH_PRIVATE_KEY`

## Strategy
Directional-only paper (BTC/ETH 1h + 15m). Arb/dep-arb execution OFF. TV observe/context.
Tier engine + learning from settled evidence. Env source: `scripts/apply-loop-arch-env.py`.
