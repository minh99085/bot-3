# Transfer Bot-3 learned lessons (NOT 30d raw data) to Bot-1 VPS.
#
# Run from your Windows laptop (has id_ed25519 authorized on Bot-1):
#   .\scripts\transfer-lessons-to-bot1.ps1
#
# Default Bot-1:
#   ssh -i $env:USERPROFILE\.ssh\id_ed25519 linuxuser@45.32.227.242
[CmdletBinding()]
param(
    [string]$Bot1Host = "45.32.227.242",
    [string]$Bot1User = "linuxuser",
    [string]$Bot1SshKey = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$Bot1Repo = "/opt/Bot-1",
    [string]$Bot3Host = "207.246.96.45",
    [string]$Bot3User = "root",
    [string]$Bot3SshKey = "$env:USERPROFILE\.ssh\bot3_cloud_agent",
    [string]$Workdir = "/tmp/bot3-lessons-for-bot1"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$BundleLocal = Join-Path $RepoRoot "data\bot3-lessons\bot3-lessons-for-bot1.tar.gz"

function Invoke-Ssh1([string]$RemoteCmd) {
    & ssh.exe -i $Bot1SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${Bot1User}@${Bot1Host}" $RemoteCmd
    if ($LASTEXITCODE -ne 0) { throw "Bot-1 SSH failed: $RemoteCmd" }
}

Write-Host "==> 1) Probe Bot-1 SSH read/write"
if (-not (Test-Path $Bot1SshKey)) {
    throw "Missing Bot-1 key: $Bot1SshKey"
}
Invoke-Ssh1 "echo BOT1_OK; whoami; hostname; touch /tmp/bot3-lessons-rw-probe && rm -f /tmp/bot3-lessons-rw-probe && echo BOT1_RW_OK; ls -d $Bot1Repo 2>/dev/null || ls -d /opt/Bot-1 /home/linuxuser/Bot-1 2>/dev/null || true"

Write-Host "==> 2) Ensure lessons bundle (~15KB) exists"
New-Item -ItemType Directory -Force -Path (Split-Path $BundleLocal -Parent) | Out-Null
if (-not (Test-Path $BundleLocal)) {
    $AltKey = "$env:USERPROFILE\.ssh\hermes-laptop-vps"
    $Key3 = if (Test-Path $Bot3SshKey) { $Bot3SshKey } elseif (Test-Path $AltKey) { $AltKey } else { $null }
    if (-not $Key3) {
        throw "Missing local bundle and no Bot-3 SSH key to fetch it. git pull origin main first."
    }
    Write-Host "    fetching lessons from Bot-3 ($Bot3Host)..."
    & scp.exe -i $Key3 -o StrictHostKeyChecking=no `
        "${Bot3User}@${Bot3Host}:/opt/Bot-3/data/bot3-lessons/bot3-lessons-for-bot1.tar.gz" `
        $BundleLocal
    if ($LASTEXITCODE -ne 0) { throw "Failed to fetch lessons from Bot-3" }
}
Get-Item $BundleLocal | Format-List FullName, Length

Write-Host "==> 3) Upload lessons to Bot-1 (no GB data)"
Invoke-Ssh1 "mkdir -p $Workdir && rm -rf $Workdir/*"
& scp.exe -i $Bot1SshKey -o StrictHostKeyChecking=no $BundleLocal "${Bot1User}@${Bot1Host}:${Workdir}/bot3-lessons-for-bot1.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "SCP to Bot-1 failed" }
Invoke-Ssh1 "cd $Workdir && tar -xzf bot3-lessons-for-bot1.tar.gz && ls -lah"

Write-Host "==> 4) Import lessons into Bot-1 /data + restart training"
$remote = @'
set -euo pipefail
WORKDIR=/tmp/bot3-lessons-for-bot1
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

lane_src = src / "lane_15m_learner_offline_prior.json"
if lane_src.exists():
    shutil.copy2(lane_src, data / "lane_15m_learner_offline_prior.json")
    print("lane_prior: copied")

rep = src / "offline_walk_forward_report.json"
if rep.exists():
    shutil.copy2(rep, data / "offline_walk_forward_report.json")

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
        floor = float((bundle.get("suggested_env") or {}).get("PULSE_MIN_ENTRY_PRICE", "0.52") or 0.52)
        if float(live_pol.get("min_entry_price") or 0) < floor:
            live_pol["min_entry_price"] = floor
        if float(live_pol.get("sweet_min") or 0) < floor:
            live_pol["sweet_min"] = floor
        live_lane["policy"] = live_pol
        live_lane["offline_prior_imported_at"] = stamp
        live_lane["last_action"] = "bot3_lessons_import"
        acct["lane_15m_learner"] = live_lane
    for k in ("chronos", "binary_intel", "p_exec_tune"):
        if k in lessons and not acct.get(k):
            acct[k] = lessons[k]
    ledger["accounting_state"] = acct
    shutil.copy2(ledger_path, data / ("btc_pulse_ledger.pre_bot3_%s.json" % stamp))
    ledger_path.write_text(json.dumps(ledger, indent=2))
    print("ledger_cells:", len((acct.get("cell_learning") or {}).get("cells") or {}))
else:
    print("WARN: no btc_pulse_ledger.json — file priors only")

manifest = {
    "imported_at": datetime.now(timezone.utc).isoformat(),
    "source": "bot3_lessons_export",
    "bundle_exported_at": bundle.get("exported_at"),
    "suggested_env": bundle.get("suggested_env"),
    "note": "Apply suggested_env via Bot-1 .env, then recreate training container",
}
(data / "bot3_lessons_import_manifest.json").write_text(json.dumps(manifest, indent=2))
print("IMPORT_OK")
print(json.dumps(manifest, indent=2))
PY
docker restart "$C"
sleep 8
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'hermes|bot' || true
echo BOT1_LESSONS_WIRED
'@

$remote | & ssh.exe -i $Bot1SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${Bot1User}@${Bot1Host}" "sudo bash -s"
if ($LASTEXITCODE -ne 0) { throw "Bot-1 import failed" }

Write-Host ""
Write-Host "Done. Lessons (~15KB, 240 cells) imported to Bot-1. No 30d GB data transferred."
Write-Host "Optional favorites env on Bot-1 .env:"
Write-Host "  PULSE_AB_PROFILE=favorites"
Write-Host "  PULSE_MIN_ENTRY_PRICE=0.52"
Write-Host "  PULSE_CELL_LEARNING_PHASE2_ENABLED=1"
Write-Host "  PULSE_CHRONOS_ENABLED=1"
Write-Host "Then recreate Bot-1 training container so env takes effect."
