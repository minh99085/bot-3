# Bot 3 deploy policy (operator rule — ALWAYS)

**Operator mandate (2026-07-12):** For **Bot 3** (`bot-3-clone-of-bot-1-`):

1. **Always push to `main`** — commit directly on `main`. **Do not create feature branches or PRs.**
2. **Always push to VPS** after every push to `origin/main` — job incomplete until VPS matches `main`.
3. **Always remove orphans and rebuild** after every VPS sync:
   `docker compose down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`.

No `-SkipRebuild`. No `docker compose restart` shortcuts unless the operator explicitly requests
code-only sync in the current message.

## Bot 3 targets

| Item | Value |
|------|-------|
| GitHub repo | `https://github.com/minh99085/bot-3-clone-of-bot-1-` |
| Default branch | `main` (only) |
| Local workspace | `C:\hermes-agent\bot-3-clone-of-bot-1-` |
| VPS host | `root@144.202.122.120` |
| VPS path | `/opt/Bot-3` |
| Dashboard | http://144.202.122.120/dashboard (`Bot 3 Directional`) |
| TradingView webhook | http://144.202.122.120/webhooks/tradingview |
| Deploy (Windows) | `.\scripts\sync-vps-bot3.ps1` |
| Deploy (Linux/bash) | `./scripts/sync-vps-bot3.sh` |
| Env setup on VPS | `python3 scripts/setup-vps-training-env.py` |
| SSH key | `$env:USERPROFILE\.ssh\bot1_grok_temp` / `~/.ssh/bot1_grok_temp` |
| Profile | `scripts/bot-profile.json` |

## Required sequence (every ship)

1. `git checkout main` && `git pull --ff-only origin main`
2. Edit → test → `git commit` on `main`
3. `git push origin main`
4. `.\scripts\sync-vps-bot3.ps1` (or `./scripts/sync-vps-bot3.sh`)
   - sync VPS HEAD to `origin/main`
   - `python3 scripts/setup-vps-training-env.py`
   - `validate-frozen-lock.py`
   - `docker compose down --remove-orphans`
   - `docker compose build`
   - `docker compose up -d --force-recreate --remove-orphans`
5. `.\scripts\verify-sync-bot3.ps1` — VPS HEAD == `origin/main`

## Port 80 note

Only one bot may bind host port 80. Stop Bot-1 on the same VPS before Bot-3 deploy if both would conflict.
