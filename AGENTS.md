# AGENTS.md

## Cursor Cloud specific instructions

This repository was reset after retiring **Bot 3**. It contains no application code until a new bot is scaffolded.

### VPS baseline (still available)

- **Host:** `207.246.96.45` (user `root`)
- **State:** Wiped — no `/opt/Bot-3`, no running containers, no cron jobs
- **SSH:** Cloud agent key at `~/.ssh/bot3_cloud_agent` (or `BOT3_VPS_SSH_PRIVATE_KEY` secret)

### VM baseline (cloud agent environment)

- Python 3.12
- Node.js v22
- Docker available on VPS

### When building the new bot

1. Add application code and dependency manifests to the repo root.
2. Document install/run commands in `README.md`.
3. Create deploy scripts for the chosen VPS path.
4. Set the VM update script to match the dependency install command documented in the new bot's README.
