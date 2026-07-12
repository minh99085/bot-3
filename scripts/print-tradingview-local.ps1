# Print TradingView webhook URLs for local Bot 3.
$Root = Split-Path -Parent $PSScriptRoot
$SecretFile = Join-Path $Root "hermes-agent-main\plugins\hermes-trading-engine\tradingview.secret"
$DashboardPort = 8810

Write-Host ""
Write-Host "=== Bot 3 TradingView local feed ===" -ForegroundColor Cyan

if (-not (Test-Path $SecretFile)) {
    Write-Host "MISSING: $SecretFile"
    Write-Host "Copy tradingview.secret.example to tradingview.secret and paste your secret."
    exit 1
}

$secret = ""
Get-Content $SecretFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    if ($line -eq "PASTE_YOUR_SECRET_HERE") { return }
    if ($line -like "TRADINGVIEW_WEBHOOK_SECRET=*") {
        $secret = $line.Split("=", 2)[1].Trim().Trim('"')
    } else {
        $secret = $line
    }
}

if (-not $secret) {
    Write-Host "Secret file exists but is empty. Paste your secret in:" -ForegroundColor Yellow
    Write-Host "  $SecretFile"
    exit 1
}

Write-Host "Secret loaded (length $($secret.Length) chars)" -ForegroundColor Green
Write-Host ""
Write-Host "TradingView alert webhook URL:"
Write-Host "  Public (use ngrok):  https://YOUR-SUBDOMAIN.ngrok-free.app/webhooks/tradingview"
Write-Host "  Start tunnel:        ngrok http $DashboardPort"
Write-Host ""
Write-Host "Local test (Docker must be running):"
Write-Host "  .\scripts\test-tradingview-webhook.ps1"
Write-Host ""
Write-Host "Pine chart inputs:"
Write-Host "  Hermes webhook secret = (same as tradingview.secret)"
Write-Host "  Symbol = BTCUSD or INDEX:BTCUSD"
Write-Host ""
Write-Host "Scripts folder: hermes-agent-main\plugins\hermes-trading-engine\tradingview\"
