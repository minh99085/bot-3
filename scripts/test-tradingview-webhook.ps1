# Send a test TradingView-style alert to local Bot 3.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$SecretFile = Join-Path $Root "hermes-agent-main\plugins\hermes-trading-engine\tradingview.secret"
$Url = "http://127.0.0.1:8810/webhooks/tradingview"

$secret = ""
if (Test-Path $SecretFile) {
    Get-Content $SecretFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line -eq "PASTE_YOUR_SECRET_HERE") { return }
        if ($line -like "TRADINGVIEW_WEBHOOK_SECRET=*") {
            $script:secret = $line.Split("=", 2)[1].Trim().Trim('"')
        } else {
            $script:secret = $line
        }
    }
}

if (-not $secret) {
    Write-Host "Set your secret in $SecretFile first." -ForegroundColor Red
    exit 1
}

$body = @{
    secret = $secret
    bot_name = "hermes"
    symbol = "BTCUSD"
    timeframe = "5"
    direction = "UP"
    strength = 0.82
    indicator_name = "local_test"
    event_id = "bot3-local-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
    bar_time = [string][int][double]::Parse((Get-Date -UFormat %s))
} | ConvertTo-Json

Write-Host "POST $Url"
$response = Invoke-RestMethod -Method POST -Uri $Url -ContentType "application/json" -Body $body
Write-Host ($response | ConvertTo-Json -Depth 5)
