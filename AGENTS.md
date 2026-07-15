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

### Git workflow

- **Always commit and push directly to `main`.** Do not create feature branches.
- Do not open PRs from separate branches unless the user explicitly asks.
- After changes: `git add`, `git commit`, `git push -u origin main`.

### Architecture pointers

- Living skills: `knowledge/SKILL.md`, `ALPHA_RESEARCH_SKILL.md`
- Memory: `knowledge/STATE.md`, `LESSONS.md`
- Verifier is sacred: `hermes/verifier.py`
- **Paper lock:** `HERMES_PAPER_ONLY=1` — live trading disabled in this deployment
- Compose: `bot` + `dashboard` + `nginx` (`deploy/nginx/nginx.conf`)
