#!/usr/bin/env bash
# Fix bind-mount permissions then drop to hermes user.
set -euo pipefail
if [[ "$(id -u)" -eq 0 ]]; then
  mkdir -p /app/logs /app/data/paper /app/data/live /app/data/handoff /app/knowledge
  chown -R hermes:hermes /app/logs /app/data /app/knowledge 2>/dev/null || true
  exec gosu hermes "$0" "$@"
fi
exec "$@"
