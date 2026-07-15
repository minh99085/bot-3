#!/usr/bin/env bash
# Docker HEALTHCHECK for bot — heartbeat file + optional HTTP
set -euo pipefail
HB="${HERMES_LOG_DIR:-/app/logs}/heartbeat.json"
MAX_AGE="${HERMES_HEARTBEAT_MAX_AGE:-900}"  # 15 min default

if [[ ! -f "$HB" ]]; then
  # Allow start_period; fail only if missing after boot
  echo "heartbeat missing"
  exit 1
fi

# Prefer HTTP health if listening
if curl -fsS "http://127.0.0.1:${HERMES_HEALTH_PORT:-8080}/health" >/dev/null 2>&1; then
  exit 0
fi

# Fallback: mtime age of heartbeat
python - <<PY
import json, os, sys, time
from pathlib import Path
p = Path("${HB}")
max_age = int("${MAX_AGE}")
try:
    data = json.loads(p.read_text())
    ts = float(data.get("ts_epoch", 0))
except Exception:
    ts = p.stat().st_mtime
age = time.time() - ts
if age > max_age:
    print(f"heartbeat stale age={age:.0f}s")
    sys.exit(1)
print(f"ok age={age:.0f}s")
PY
