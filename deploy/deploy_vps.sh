#!/usr/bin/env bash
# Deploy Hermes v2 Paper Docker stack to VPS
# Workflow: push main → sync VPS → compose down --remove-orphans → up -d --build --remove-orphans
# Dashboard: http://<VPS_IP>/dashboard
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${VPS_HOST:-207.246.96.45}"
USER="${VPS_USER:-root}"
REMOTE_PATH="${VPS_PATH:-/opt/financial-freedom-bot}"
KEY="${VPS_SSH_KEY:-$HOME/.ssh/bot3_cloud_agent}"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Write key from Cursor secret if provided
if [[ -n "${BOT3_VPS_SSH_PRIVATE_KEY:-}" ]]; then
  printf '%s\n' "$BOT3_VPS_SSH_PRIVATE_KEY" > "$KEY"
  chmod 600 "$KEY"
  echo "Using SSH key from BOT3_VPS_SSH_PRIVATE_KEY"
fi

SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)
RSYNC=(rsync -az --delete)
if [[ -f "$KEY" ]]; then
  SSH+=( -i "$KEY" )
  RSYNC+=( -e "ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new" )
fi

echo "Testing SSH to ${USER}@${HOST}..."
if ! "${SSH[@]}" "${USER}@${HOST}" "echo ok" 2>/dev/null; then
  echo ""
  echo "ERROR: Cannot SSH to ${USER}@${HOST}"
  echo ""
  echo "Fix one of the following, then re-run ./deploy/deploy_vps.sh:"
  echo ""
  echo "  A) Add Cursor secret BOT3_VPS_SSH_PRIVATE_KEY (private key for root@${HOST})"
  echo "     Cursor → Cloud Agents → Environments → bot-3 → Secrets"
  echo ""
  echo "  B) Add this cloud-agent public key to VPS /root/.ssh/authorized_keys:"
  if [[ -f "${KEY}.pub" ]]; then
    cat "${KEY}.pub"
  elif [[ -f "$KEY" ]]; then
    ssh-keygen -y -f "$KEY" 2>/dev/null || true
  fi
  echo ""
  echo "  C) Run bootstrap on the VPS console (no SSH from here needed):"
  echo "     curl -fsSL https://raw.githubusercontent.com/minh99085/bot-3/main/deploy/bootstrap_on_vps.sh | bash"
  echo ""
  exit 1
fi

echo "Syncing Hermes Paper to ${USER}@${HOST}:${REMOTE_PATH}"
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
  --exclude 'data/parquet/*' \
  --exclude 'data/models/*' \
  --exclude 'data/archive/*' \
  --exclude 'logs/*' \
  --exclude 'artifacts/*' \
  --exclude '.env' \
  "$ROOT/" "${USER}@${HOST}:${REMOTE_PATH}/"

"${SSH[@]}" "${USER}@${HOST}" "bash -s" <<EOF
set -euo pipefail
cd ${REMOTE_PATH}

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
sed -i 's/^HERMES_PAPER_ONLY=.*/HERMES_PAPER_ONLY=1/' .env || true
sed -i 's/^HERMES_LIVE=.*/HERMES_LIVE=0/' .env || true
grep -q '^HERMES_PAPER_ONLY=' .env || echo 'HERMES_PAPER_ONLY=1' >> .env
grep -q '^HERMES_LIVE=' .env || echo 'HERMES_LIVE=0' >> .env
grep -q '^HERMES_CAPITAL=' .env || echo 'HERMES_CAPITAL=2000' >> .env
grep -q '^HERMES_SCOPE_BTC_UPDOWN_ONLY=' .env || echo 'HERMES_SCOPE_BTC_UPDOWN_ONLY=1' >> .env
grep -q '^HERMES_BTC_UPDOWN_SLUGS=' .env || echo 'HERMES_BTC_UPDOWN_SLUGS=btc-updown-15m-1784113200,btc-updown-5m-1784113500' >> .env
sed -i 's/^HERMES_SCOPE_BTC_UPDOWN_ONLY=.*/HERMES_SCOPE_BTC_UPDOWN_ONLY=1/' .env || true

LANES=(
  lane01_baseline lane02_chainlink lane03_favorite lane04_longshot lane05_late
  lane06_garch lane07_marketsigma lane08_legacy lane09_random lane10_depth
)
for lane in "\${LANES[@]}"; do
  mkdir -p "data/paper/\${lane}" "data/handoff/\${lane}" "logs/\${lane}" "artifacts/\${lane}"
done
mkdir -p data/live knowledge
chown -R 10001:10001 logs data knowledge artifacts 2>/dev/null || true
touch data/paper/.gitkeep logs/.gitkeep
# remove obsolete single-bot container name if present
docker rm -f hermes-bot 2>/dev/null || true

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH || true
  ufw allow 80/tcp || true
  ufw --force enable || true
  echo "UFW: SSH + 80 allowed; 8501 stays closed"
fi

# Mandatory rebuild path: down → remove orphans → build/up
echo "compose down --remove-orphans"
if docker compose version >/dev/null 2>&1; then
  docker compose down --remove-orphans || true
  echo "compose up -d --build --remove-orphans"
  docker compose up -d --build --remove-orphans
else
  docker-compose down --remove-orphans || true
  docker-compose up -d --build --remove-orphans
fi

# Keep systemd unit in sync (restart policy / boot)
cp deploy/hermes-paper.service /etc/systemd/system/hermes-paper.service
systemctl daemon-reload
systemctl enable hermes-paper.service

# Re-assert ownership after compose (rsync/root can leave knowledge/ unwritable)
chown -R 10001:10001 logs data knowledge artifacts 2>/dev/null || true
# Clear stale shared auto-pause left by pre-fleet risk_monitor builds
if [[ -f knowledge/STATE.md ]]; then
  sed -i 's/^\(- \*\*Pause Loop\*\*: \).*/\1false/' knowledge/STATE.md || true
  sed -i 's/^\(- \*\*Circuit Breaker\*\*: \).*/\1clear/' knowledge/STATE.md || true
  sed -i 's/^\(- \*\*Pause Reason\*\*: \).*/\1/' knowledge/STATE.md || true
  chown 10001:10001 knowledge/STATE.md 2>/dev/null || true
fi

sleep 12
docker compose ps 2>/dev/null || docker-compose ps
curl -fsS http://127.0.0.1/healthz && echo " nginx ok" || echo "WARN: nginx health pending"
EOF

echo ""
echo "=== Deployed (push main → sync VPS → down/orphans → rebuild) ==="
echo "Dashboard: http://${HOST}/dashboard"
echo "Health:    http://${HOST}/healthz"
echo "SSH logs:  ssh ${USER}@${HOST} 'docker compose -f ${REMOTE_PATH}/docker-compose.yml logs -f hermes-lane01_baseline'"
echo "Fleet:     10× BTC15 lanes lane01…lane10 (\$2k each = \$20k)"
