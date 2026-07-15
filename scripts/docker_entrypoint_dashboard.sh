#!/usr/bin/env bash
# Dashboard container entrypoint — Streamlit under /dashboard (nginx proxies)
set -euo pipefail
cd /app
export PYTHONPATH=/app
export HERMES_PAPER_ONLY="${HERMES_PAPER_ONLY:-1}"
export HERMES_LIVE=0
mkdir -p /app/logs /app/data/paper

echo "[entrypoint] Hermes dashboard on :8501 baseUrlPath=dashboard"
exec streamlit run dashboard.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.baseUrlPath=dashboard \
  --server.headless=true \
  --browser.gatherUsageStats=false
