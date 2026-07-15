#!/usr/bin/env bash
# Bot container entrypoint — paper overnight loop + health HTTP
set -euo pipefail
cd /app
export PYTHONPATH=/app
export HERMES_PAPER_ONLY="${HERMES_PAPER_ONLY:-1}"
export HERMES_LIVE=0

INSTANCE="${HERMES_INSTANCE_ID:-default}"
FILTER="${MARKET_FILTER:-${INSTANCE}}"
LOG_DIR="${HERMES_LOG_DIR:-/app/logs/${INSTANCE}}"
PAPER_DIR="${HERMES_PAPER_DIR:-/app/data/paper/${INSTANCE}}"
HANDOFF_DIR="${HERMES_HANDOFF_DIR:-/app/data/handoff/${INSTANCE}}"

export HERMES_INSTANCE_ID="${INSTANCE}"
export MARKET_FILTER="${FILTER}"
export HERMES_LOG_DIR="${LOG_DIR}"
export HERMES_PAPER_DIR="${PAPER_DIR}"
export HERMES_HANDOFF_DIR="${HANDOFF_DIR}"

mkdir -p "${LOG_DIR}" "${PAPER_DIR}" "${HANDOFF_DIR}" /app/data/live /app/knowledge "/app/artifacts/${INSTANCE}"

INTERVAL="${HERMES_INTERVAL:-300}"
echo "[entrypoint] Hermes instance=${INSTANCE} MARKET_FILTER=${FILTER} interval=${INTERVAL}s bankroll=\$${HERMES_CAPITAL:-2000}"
echo "[entrypoint] logs=${LOG_DIR} paper=${PAPER_DIR}"
exec python -m hermes.hermes_loop overnight --interval "${INTERVAL}"
