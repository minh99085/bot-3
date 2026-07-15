#!/usr/bin/env bash
# Fix bind-mount permissions then drop to hermes user.
set -euo pipefail
if [[ "$(id -u)" -eq 0 ]]; then
  mkdir -p \
    /app/logs/btc5 /app/logs/btc15 /app/logs/eth5 /app/logs/sol5 /app/logs/rotator \
    /app/data/paper/btc5 /app/data/paper/btc15 /app/data/paper/eth5 /app/data/paper/sol5 /app/data/paper/rotator \
    /app/data/handoff/btc5 /app/data/handoff/btc15 /app/data/handoff/eth5 /app/data/handoff/sol5 /app/data/handoff/rotator \
    /app/data/live \
    /app/artifacts/btc5 /app/artifacts/btc15 /app/artifacts/eth5 /app/artifacts/sol5 /app/artifacts/rotator \
    /app/knowledge
  chown -R hermes:hermes /app/logs /app/data /app/knowledge /app/artifacts 2>/dev/null || true
  exec gosu hermes "$0" "$@"
fi
exec "$@"
