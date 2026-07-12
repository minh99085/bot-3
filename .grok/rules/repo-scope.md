# Repo scope (Bot 3)

Work only in `https://github.com/minh99085/bot-3-clone-of-bot-1-`.

Never commit or push to `hermes-agent-cursor` or `minh99085/Bot-1` unless the operator explicitly says otherwise in the current turn.

## Git workflow (operator rule 2026-07-12)

- **Default branch:** `main` — commit here only.
- **Do not create feature branches or PRs** — no `cursor/*` branches.
- After every `git push origin main`, run VPS deploy (see below).

## VPS deploy — MANDATORY after every push to `main`

**Full policy:** `.grok/rules/bot3-deploy-policy.md`

**Non-negotiable:** After every VPS sync, **always remove orphans and rebuild**.
Push → `.\scripts\sync-vps-bot3.ps1` or `./scripts/sync-vps-bot3.sh` → `verify-sync-bot3.ps1`.
Execute yourself; never leave VPS stale.

### Standard sequence

1. `git push origin main` (local `HEAD` == `origin/main`)
2. `.\scripts\sync-vps-bot3.ps1` — sync VPS, `setup-vps-training-env.py`, validate frozen lock,
   `down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`
3. **Never** `-SkipRebuild` unless operator explicitly requests code-only sync

### VPS access (Bot 3)

- Host: `144.202.122.120`, user `root`, repo: `/opt/Bot-3`
- Dashboard: http://144.202.122.120/dashboard
- TradingView: http://144.202.122.120/webhooks/tradingview
- SSH key: `$env:USERPROFILE\.ssh\bot1_grok_temp` / `~/.ssh/bot1_grok_temp`
- Plugin compose: `/opt/Bot-3/hermes-agent-main/plugins/hermes-trading-engine`
- Profile: `scripts/bot-profile.json`

## Destructive change guard

Read **`.grok/rules/destructive-change-guard.md`** before any delete/remove/disable that could damage the bot.
