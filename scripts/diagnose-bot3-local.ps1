# Bot 3 — diagnose local Docker training + dashboard.
# Run from repo root:  .\scripts\diagnose-bot3-local.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Plugin = Join-Path $Root "hermes-agent-main\plugins\hermes-trading-engine"
$Project = "bot3-local"
$Compose = @("-p", $Project, "-f", "docker-compose.yml", "-f", "docker-compose.local.yml")

function Section($title) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
}

Set-Location $Plugin

Section "Docker Desktop"
try {
    docker version --format "Docker {{.Server.Version}}" 2>$null
} catch {
    Write-Host "FAIL: Docker not reachable. Start Docker Desktop and wait until it says Running." -ForegroundColor Red
}

Section "Bot 3 containers"
docker compose @Compose ps -a

Section "Port 8800 (dashboard)"
$port = Get-NetTCPConnection -LocalPort 8800 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($port) {
    Write-Host "OK: something is listening on port 8800 (state=$($port.State))"
} else {
    Write-Host "WARN: nothing listening on port 8800 — API container may not be up." -ForegroundColor Yellow
}

Section "Health API"
try {
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8800/api/health" -TimeoutSec 5
    Write-Host ($h | ConvertTo-Json -Depth 4)
    if (-not $h.pulse_status_fresh) {
        Write-Host "NOTE: pulse_status_fresh=false is normal for the first 1-2 minutes after start." -ForegroundColor Yellow
    }
} catch {
    Write-Host "FAIL: cannot reach http://127.0.0.1:8800/api/health" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Section "Pulse status"
try {
    $p = Invoke-RestMethod -Uri "http://127.0.0.1:8800/api/polymarket/training/btc_pulse" -TimeoutSec 5
    if ($p.available) {
        Write-Host "OK: training loop has written status (ticks=$($p.ticks))"
    } else {
        Write-Host "WAIT: $($p.reason)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "SKIP: pulse status not available yet."
}

Section "Last 25 lines — bot3-hermes-trading-engine (dashboard/API)"
docker logs --tail 25 bot3-hermes-trading-engine 2>&1

Section "Last 25 lines — bot3-hermes-training (training loop)"
docker logs --tail 25 bot3-hermes-training 2>&1

Section "Quick fixes"
Write-Host @"
1. Restart everything:
     .\scripts\run-bot3-local-training.ps1
2. Dashboard URL (try both):
     http://127.0.0.1:8800/dashboard
     http://localhost:8800/dashboard
3. If port 8800 is taken, edit hermes-agent-main\plugins\hermes-trading-engine\.env
     PULSE_DASHBOARD_PUBLISH=0.0.0.0:8801
   then re-run run-bot3-local-training.ps1 and open http://127.0.0.1:8801/dashboard
4. Live logs:
     cd hermes-agent-main\plugins\hermes-trading-engine
     docker compose -p bot3-local -f docker-compose.yml -f docker-compose.local.yml logs -f hermes-training
"@
