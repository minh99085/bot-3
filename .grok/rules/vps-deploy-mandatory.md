# VPS deploy — mandatory sequence (Bot 3)

**ALWAYS:** push to `main` → sync VPS → remove orphans → rebuild.
No feature branches. No PRs. Never `-SkipRebuild` unless operator requests code-only sync.

## Required sequence

1. Local `HEAD` == `origin/main`
2. `./scripts/sync-vps-bot3.sh` or `.\scripts\sync-vps-bot3.ps1`
3. On VPS: `setup-vps-training-env.py` → validate → `down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`
4. Verify VPS HEAD == `origin/main`

## Bot 3 targets

| Item | Value |
|------|-------|
| Repo | `https://github.com/minh99085/bot-3-clone-of-bot-1-` |
| Branch | `main` only |
| VPS | `root@207.246.96.45` |
| Path | `/opt/Bot-3` |
| Dashboard | `http://207.246.96.45/dashboard` |
| Scripts | `sync-vps-bot3.ps1` / `sync-vps-bot3.sh` |
| Policy | `.grok/rules/bot3-deploy-policy.md` |
| SSH (cloud) | `~/.ssh/bot3_cloud_agent` or `BOT3_VPS_SSH_PRIVATE_KEY` |
