---
name: pulse-babysit
description: >-
  Autonomous Bot 3 directional paper loop: deploy to VPS, pull reports,
  score trading performance, diagnose issues, fix code, commit/push main, sync-vps-bot3
  with orphan cleanup and rebuild, repeat. Use for hands-off bot iteration or /pulse-babysit.
argument-hint: "cycle | force-eval | status | deploy"
---

# Pulse Babysit (Bot 3 closed loop)

Operate **Bot 3 Directional** paper bot without asking between cycles. PAPER ONLY — never enable live.

**Team identity:** quant research + engineer + trader. Target selective high WR.

**No soak:** continuous loop from live settled evidence.

## Repo anchors

| Item | Path |
|------|------|
| Workspace | `C:\hermes-agent\bot-3-clone-of-bot-1-` |
| Plugin | `hermes-agent-main/plugins/hermes-trading-engine` |
| Deploy | `.\scripts\sync-vps-bot3.ps1` / `./scripts/sync-vps-bot3.sh` |
| VPS | `root@207.246.96.45` `/opt/Bot-3` |
| Dashboard | `http://207.246.96.45/dashboard` |
| Policy | `.grok/rules/bot3-deploy-policy.md` |
| State | `scripts/pulse-babysit/state.json` |

## Commands

| Command | Behavior |
|---------|----------|
| `cycle` | Default loop iteration |
| `force-eval` | Pull + evaluate now |
| `status` | Print state + last evaluation |
| `deploy` | `git push origin main` + full VPS rebuild |

## Cycle steps

1. Read `scripts/pulse-babysit/state.json`.
2. `python scripts/pulse-babysit/scan-health.py`
3. `python scripts/pulse-babysit/validate-frozen-lock.py`
4. `./scripts/pulse-babysit/pull-vps-artifacts.sh` (or `.ps1`)
5. `python scripts/pulse-babysit/evaluate-cycle.py`
6. Optional WR tune via `apply-wr-tune.py` when evidence supports it
7. Fix at most 2 highest-severity issues; run targeted tests
8. Commit on `main` → `git push origin main`
9. **MANDATORY:** `./scripts/sync-vps-bot3.sh` (orphans + rebuild)

Never create feature branches or PRs.
