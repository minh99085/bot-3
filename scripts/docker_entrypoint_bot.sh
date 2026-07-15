#!/usr/bin/env bash
# Bot container entrypoint — paper overnight loop + health HTTP
set -euo pipefail
cd /app
export PYTHONPATH=/app
export HERMES_PAPER_ONLY="${HERMES_PAPER_ONLY:-1}"
export HERMES_LIVE=0
mkdir -p /app/logs /app/data/paper /app/data/handoff /app/knowledge

INTERVAL="${HERMES_INTERVAL:-300}"
echo "[entrypoint] Hermes v2 Paper bot starting (interval=${INTERVAL}s, bankroll=\$${HERMES_CAPITAL:-2000})"
exec python -m hermes.hermes_loop overnight --interval "${INTERVAL}"
