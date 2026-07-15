# AGENTS.md

## Cursor Cloud specific instructions

**Hermes v2 Paper** — 24/7 Polymarket paper stack ($2000 bankroll). Dashboard at `http://<VPS_IP>/dashboard`.

### VPS baseline

- **Host:** `207.246.96.45` (user `root`)
- **Deploy path:** `/opt/financial-freedom-bot`
- **SSH:** `~/.ssh/bot3_cloud_agent` (or `BOT3_VPS_SSH_PRIVATE_KEY`)
- **Deploy:** `./deploy/deploy_vps.sh` (Docker Compose + nginx + systemd)
- **Public ports:** **80 only** (nginx). Do **not** expose 8501.

### VM baseline (cloud agent environment)

- Python 3.12
- Node.js v22
- Docker available on VPS

### Install / run (keep in sync with README)

```bash
# Local Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=. HERMES_PAPER_ONLY=1
python -m hermes.hermes_loop overnight
streamlit run dashboard.py --server.baseUrlPath=dashboard
pytest -q

# Docker (preferred for VPS)
cp .env.example .env
docker compose up -d --build
# → http://localhost/dashboard
```

### Git + VPS deploy workflow (mandatory)

After every code change, always do this sequence — no feature branches, no PRs unless asked:

1. **Commit and push to `main`**
   ```bash
   git add -A && git commit -m "..." && git push -u origin main
   ```
2. **Sync VPS** (rsync via `./deploy/deploy_vps.sh`)
3. **On VPS: compose down, remove orphans, rebuild**
   ```bash
   docker compose down --remove-orphans
   docker compose up -d --build --remove-orphans
   ```

`./deploy/deploy_vps.sh` performs steps 2–3 automatically after a successful SSH check.

When a deploy round is finished, end with: **I am done thinking, push to main vps and rebuild**

### Architecture pointers

- Living skills: `knowledge/SKILL.md`, `ALPHA_RESEARCH_SKILL.md`
- Memory: `knowledge/STATE.md`, `LESSONS.md`
- Verifier is sacred: `hermes/verifier.py`
- **Paper lock:** `HERMES_PAPER_ONLY=1` — live trading disabled in this deployment
- **Market scope:** BTC Up/Down 5m + 15m only
- Compose: `bot` + `dashboard` + `nginx` (`deploy/nginx/nginx.conf`)
