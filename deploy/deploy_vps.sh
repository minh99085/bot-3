#!/usr/bin/env bash
# Deploy Hermes v2 Paper Docker stack to VPS
# Dashboard: http://<VPS_IP>/dashboard
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${VPS_HOST:-207.246.96.45}"
USER="${VPS_USER:-root}"
REMOTE_PATH="${VPS_PATH:-/opt/financial-freedom-bot}"
KEY="${VPS_SSH_KEY:-$HOME/.ssh/bot3_cloud_agent}"

SSH=(ssh -o StrictHostKeyChecking=accept-new)
RSYNC=(rsync -az --delete)
if [[ -f "$KEY" ]]; then
  SSH+=( -i "$KEY" )
  RSYNC+=( -e "ssh -i $KEY -o StrictHostKeyChecking=accept-new" )
fi

echo "Deploying Hermes Paper to ${USER}@${HOST}:${REMOTE_PATH}"
"${SSH[@]}" "${USER}@${HOST}" "mkdir -p ${REMOTE_PATH}"

"${RSYNC[@]}" \
  --exclude '.venv' \
  --exclude '.git' \
  --exclude '.worktrees' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude 'data/paper/*' \
  --exclude 'data/live/*' \
  --exclude 'data/handoff/*' \
  --exclude 'logs/*' \
  --exclude '.env' \
  "$ROOT/" "${USER}@${HOST}:${REMOTE_PATH}/"

"${SSH[@]}" "${USER}@${HOST}" "bash -s" <<EOF
set -euo pipefail
cd ${REMOTE_PATH}

# Env
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
# Force paper lock on VPS
sed -i 's/^HERMES_PAPER_ONLY=.*/HERMES_PAPER_ONLY=1/' .env || true
sed -i 's/^HERMES_LIVE=.*/HERMES_LIVE=0/' .env || true
grep -q '^HERMES_PAPER_ONLY=' .env || echo 'HERMES_PAPER_ONLY=1' >> .env
grep -q '^HERMES_LIVE=' .env || echo 'HERMES_LIVE=0' >> .env
grep -q '^HERMES_CAPITAL=' .env || echo 'HERMES_CAPITAL=2000' >> .env

mkdir -p data/paper data/live data/handoff logs knowledge
touch data/paper/.gitkeep logs/.gitkeep

# Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# Firewall: only HTTP (and SSH). Do NOT open 8501.
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH || true
  ufw allow 80/tcp || true
  ufw --force enable || true
  echo "UFW: SSH + 80 allowed; 8501 stays closed"
fi

# systemd unit
cp deploy/hermes-paper.service /etc/systemd/system/hermes-paper.service
systemctl daemon-reload
systemctl enable hermes-paper.service
systemctl restart hermes-paper.service

sleep 8
docker compose ps || docker-compose ps
echo ""
echo "Dashboard: http://${HOST}/dashboard"
echo "Health:    http://${HOST}/healthz"
echo "Logs:      journalctl -u hermes-paper -f"
echo "           docker compose logs -f bot dashboard nginx"
EOF
