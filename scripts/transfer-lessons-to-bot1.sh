#!/usr/bin/env bash
# Transfer Bot-3 learned lessons (NOT 30d raw data) to Bot-1 VPS.
#
# Cloud agents usually CANNOT reach Bot-1 (SSH reset / IP allowlist).
# Run from your LAPTOP (has id_ed25519 authorized on Bot-1):
#   bash scripts/transfer-lessons-to-bot1.sh
#   # or Windows:
#   .\scripts\transfer-lessons-to-bot1.ps1
#
# Default Bot-1:
#   ssh -i ~/.ssh/id_ed25519 linuxuser@45.32.227.242
# Bundle is ~15KB (cell priors + lane policy + suggested env). No GB dumps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOT3_HOST="${BOT3_VPS_HOST:-207.246.96.45}"
BOT3_USER="${BOT3_VPS_USER:-root}"
BOT3_KEY="${BOT3_VPS_SSH_KEY:-${HOME}/.ssh/bot3_cloud_agent}"
BOT1_HOST="${BOT1_VPS_HOST:-45.32.227.242}"
BOT1_USER="${BOT1_VPS_USER:-linuxuser}"
BOT1_KEY="${BOT1_VPS_SSH_KEY:-${HOME}/.ssh/id_ed25519}"
BOT1_REPO="${BOT1_VPS_REPO:-/opt/Bot-1}"
BUNDLE_LOCAL="${ROOT}/data/bot3-lessons/bot3-lessons-for-bot1.tar.gz"
WORKDIR="/tmp/bot3-lessons-for-bot1"

if [[ ! -f "$BOT1_KEY" ]]; then
  echo "FATAL: Bot-1 SSH key not found: $BOT1_KEY" >&2
  exit 1
fi

SSH1=(ssh -i "$BOT1_KEY" -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${BOT1_USER}@${BOT1_HOST}")
SCP1=(scp -i "$BOT1_KEY" -o StrictHostKeyChecking=no)

echo "==> 1) Probe Bot-1 SSH read/write"
"${SSH1[@]}" 'echo BOT1_OK; whoami; hostname; touch /tmp/bot3-lessons-rw-probe && rm -f /tmp/bot3-lessons-rw-probe && echo BOT1_RW_OK; ls -d '"$BOT1_REPO"' 2>/dev/null || ls -d /opt/Bot-1 /home/linuxuser/Bot-1 2>/dev/null || true'

echo "==> 2) Ensure lessons bundle exists (~15KB; pull from Bot-3 if missing)"
mkdir -p "$(dirname "$BUNDLE_LOCAL")"
if [[ ! -f "$BUNDLE_LOCAL" ]]; then
  if [[ ! -f "$BOT3_KEY" && -f "${HOME}/.ssh/hermes-laptop-vps" ]]; then
    BOT3_KEY="${HOME}/.ssh/hermes-laptop-vps"
  fi
  if [[ ! -f "$BOT3_KEY" ]]; then
    echo "FATAL: missing local bundle and no Bot-3 key to fetch it. git pull origin main." >&2
    exit 1
  fi
  echo "    fetching lessons from Bot-3..."
  scp -i "$BOT3_KEY" -o StrictHostKeyChecking=no \
    "${BOT3_USER}@${BOT3_HOST}:/opt/Bot-3/data/bot3-lessons/bot3-lessons-for-bot1.tar.gz" \
    "$BUNDLE_LOCAL"
fi
ls -lh "$BUNDLE_LOCAL"

echo "==> 3) Upload lessons (~KB) to Bot-1"
"${SSH1[@]}" "mkdir -p $WORKDIR && rm -rf $WORKDIR/*"
"${SCP1[@]}" "$BUNDLE_LOCAL" "${BOT1_USER}@${BOT1_HOST}:${WORKDIR}/bot3-lessons-for-bot1.tar.gz"
"${SSH1[@]}" "cd $WORKDIR && tar -xzf bot3-lessons-for-bot1.tar.gz && ls -lah"

echo "==> 4) Import lessons into Bot-1 /data (merge cells + lane prior + env tips)"
"${SSH1[@]}" "sudo bash -s" <<'REMOTE'
set -euo pipefail
WORKDIR=/tmp/bot3-lessons-for-bot1
# Find running training container
C=$(docker ps --format '{{.Names}}' | grep -E 'hermes-training|bot-1|Bot-1' | head -1 || true)
if [[ -z "${C:-}" ]]; then
  C=$(docker ps --format '{{.Names}}' | head -1 || true)
fi
echo "target_container=$C"
test -n "$C"

docker cp "$WORKDIR/." "$C":/tmp/bot3-lessons/

docker exec "$C" python3 - <<'PY'
import json, shutil
from pathlib import Path
from datetime import datetime, timezone

data = Path("/data")
src = Path("/tmp/bot3-lessons")
bundle = json.loads((src / "lessons_bundle.json").read_text())
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def merge_cells(live, offline):
    live_cells = dict((live or {}).get("cells") or {})
    off_cells = dict((offline or {}).get("cells") or {})
    for key, stats in off_cells.items():
        if not isinstance(stats, dict):
            continue
        cur = live_cells.get(key)
        off_t = int(stats.get("trades", 0) or 0)
        if cur is None or int(cur.get("trades", 0) or 0) < off_t:
            live_cells[key] = {
                "evals": int(stats.get("evals", 0) or 0),
                "trades": off_t,
                "wins": int(stats.get("wins", 0) or 0),
                "pnl_usd": round(float(stats.get("pnl_usd", 0) or 0), 4),
            }
    return {"schema": "directional_cell_learning/2.0", "cells": live_cells}

# 1) cell file
cell_src = src / "directional_cell_learning.json"
if cell_src.exists():
    live_path = data / "directional_cell_learning.json"
    live = json.loads(live_path.read_text()) if live_path.exists() else {}
    offline = json.loads(cell_src.read_text())
    merged = merge_cells(live, offline)
    if live_path.exists():
        shutil.copy2(live_path, data / ("directional_cell_learning.pre_bot3_%s.json" % stamp))
    live_path.write_text(json.dumps(merged, indent=2))
    print("cells_file:", len(merged["cells"]))

# 2) lane prior sidecar
lane_src = src / "lane_15m_learner_offline_prior.json"
if lane_src.exists():
    shutil.copy2(lane_src, data / "lane_15m_learner_offline_prior.json")
    print("lane_prior: copied")

# 3) offline report
rep = src / "offline_walk_forward_report.json"
if rep.exists():
    shutil.copy2(rep, data / "offline_walk_forward_report.json")

# 4) patch ledger accounting_state (so restart actually loads lessons)
ledger_path = data / "btc_pulse_ledger.json"
if ledger_path.exists():
    ledger = json.loads(ledger_path.read_text())
    acct = dict(ledger.get("accounting_state") or {})
    lessons = bundle.get("accounting_lessons") or {}
    if "cell_learning" in lessons:
        acct["cell_learning"] = merge_cells(acct.get("cell_learning") or {}, lessons["cell_learning"])
    if "lane_15m_learner" in lessons:
        live_lane = dict(acct.get("lane_15m_learner") or {})
        off_pol = (lessons["lane_15m_learner"].get("policy") or {})
        live_pol = dict(live_lane.get("policy") or {})
        live_pol.update(off_pol)
        # clamp to favorites floor if present
        floor = float((bundle.get("suggested_env") or {}).get("PULSE_MIN_ENTRY_PRICE", "0.52") or 0.52)
        if float(live_pol.get("min_entry_price") or 0) < floor:
            live_pol["min_entry_price"] = floor
        if float(live_pol.get("sweet_min") or 0) < floor:
            live_pol["sweet_min"] = floor
        live_lane["policy"] = live_pol
        live_lane["offline_prior_imported_at"] = stamp
        live_lane["last_action"] = "bot3_lessons_import"
        acct["lane_15m_learner"] = live_lane
    # optional soft-merge for other learners (only if empty)
    for k in ("chronos", "binary_intel", "p_exec_tune"):
        if k in lessons and not acct.get(k):
            acct[k] = lessons[k]
    ledger["accounting_state"] = acct
    shutil.copy2(ledger_path, data / ("btc_pulse_ledger.pre_bot3_%s.json" % stamp))
    ledger_path.write_text(json.dumps(ledger, indent=2))
    print("ledger_cells:", len((acct.get("cell_learning") or {}).get("cells") or {}))
else:
    print("WARN: no btc_pulse_ledger.json — file priors only")

# 5) write import manifest + suggested env note
manifest = {
    "imported_at": datetime.now(timezone.utc).isoformat(),
    "source": "bot3_lessons_export",
    "bundle_exported_at": bundle.get("exported_at"),
    "suggested_env": bundle.get("suggested_env"),
    "note": "Apply suggested_env via Bot-1 setup script / .env, then recreate training container",
}
(data / "bot3_lessons_import_manifest.json").write_text(json.dumps(manifest, indent=2))
print("IMPORT_OK")
print(json.dumps(manifest, indent=2))
PY

# Restart training so ledger patches load
docker restart "$C"
sleep 8
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'hermes|bot' || true
echo BOT1_LESSONS_WIRED
REMOTE

echo ""
echo "Done. Lessons (~14KB) imported to Bot-1."
echo "Optional: apply favorites env on Bot-1 (.env):"
echo "  PULSE_AB_PROFILE=favorites"
echo "  PULSE_MIN_ENTRY_PRICE=0.52"
echo "  PULSE_CELL_LEARNING_PHASE2_ENABLED=1"
echo "  PULSE_CHRONOS_ENABLED=1"
echo "Then recreate Bot-1 training container so env takes effect."
