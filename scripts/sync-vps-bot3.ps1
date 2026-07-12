# Sync origin/main -> Bot 3 VPS, then ALWAYS down --remove-orphans -> build -> up --remove-orphans.
# Operator: paste TradingView secret into tradingview.secret on the laptop before sync (scp'd with repo).
[CmdletBinding()]
param(
    [switch]$SkipRebuild,
    [switch]$VerifyOnly,
    [string]$SshKey = "$env:USERPROFILE\.ssh\hermes-laptop-vps",
    [string]$VpsHost = "207.246.96.45",
    [string]$VpsUser = "root",
    [string]$VpsRepo = "/opt/Bot-3",
    [string]$PluginPath = "/opt/Bot-3/hermes-agent-main/plugins/hermes-trading-engine",
    [string]$GithubRepo = "https://github.com/minh99085/bot-3-clone-of-bot-1-.git"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-Error "Not a git repo: $RepoRoot"
}
if ($RepoRoot -notmatch "bot-3") {
    Write-Warning "Repo path does not contain 'bot-3' — confirm this is the Bot 3 clone before deploying."
}
Set-Location $RepoRoot

if ($VerifyOnly) {
    & "$PSScriptRoot\verify-sync-bot3.ps1" -VpsHost $VpsHost -VpsRepo $VpsRepo -SshKey $SshKey
    exit $LASTEXITCODE
}

function Get-ShortSha([string]$sha) { if ($sha.Length -ge 7) { $sha.Substring(0, 7) } else { $sha } }

function Invoke-SshCmd([string]$RemoteCmd) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & ssh.exe -i $SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${VpsUser}@${VpsHost}" $RemoteCmd
    $ErrorActionPreference = $prev
    if ($null -eq $out) { return "" }
    if ($out -is [array]) { return ($out[-1] | Out-String).Trim() }
    return "$out".Trim()
}

function Invoke-SshScript([string]$Body) {
    $localScript = Join-Path $env:TEMP "grok-bot3-remote-$([Guid]::NewGuid().ToString('N')).sh"
    $remoteScript = "/tmp/grok-bot3-remote-$([Guid]::NewGuid().ToString('N')).sh"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($localScript, ($Body -replace "`r`n", "`n"), $utf8NoBom)
    & scp.exe -i $SshKey -o StrictHostKeyChecking=no $localScript "${VpsUser}@${VpsHost}:$remoteScript"
    Invoke-SshCmd "bash $remoteScript; rm -f $remoteScript"
    Remove-Item $localScript -Force -ErrorAction SilentlyContinue
}

$doRebuild = -not $SkipRebuild
Write-Host "BOT3 deploy -> $VpsUser@${VpsHost}:$VpsRepo"

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& git fetch origin main 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
$local = (git rev-parse HEAD).Trim()
$origin = (git rev-parse origin/main 2>$null).Trim()
if (-not $origin) { $origin = $local }

if ($local -ne $origin) {
    $mergeBase = (git merge-base HEAD origin/main 2>$null).Trim()
    if ($mergeBase -eq $local -and $local -ne $origin) {
        Write-Host "Local behind origin/main — fast-forward pull..."
        git pull --ff-only origin main
        $local = (git rev-parse HEAD).Trim()
    }
    if ($local -ne $origin) {
        Write-Error "Local HEAD ($local) != origin/main ($origin). Push or pull first."
    }
}

$origin = "$origin".Trim().ToLowerInvariant()

$vpsHead = (& ssh.exe -i $SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${VpsUser}@${VpsHost}" "git -C $VpsRepo rev-parse HEAD 2>/dev/null || echo MISSING").Trim().ToLowerInvariant()
if ($vpsHead -notmatch '^[0-9a-f]{40}$') {
    Start-Sleep -Seconds 2
    $vpsHead = (& ssh.exe -i $SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${VpsUser}@${VpsHost}" "git -C $VpsRepo rev-parse HEAD 2>/dev/null || echo MISSING").Trim().ToLowerInvariant()
    if ($vpsHead -notmatch '^[0-9a-f]{40}$') { $vpsHead = "MISSING" }
}

Write-Host "origin/main : $(Get-ShortSha $origin) $origin"
Write-Host "VPS HEAD    : $(Get-ShortSha $vpsHead) $vpsHead"

if ($vpsHead -eq $origin) {
    Write-Host "SYNC OK - VPS already matches origin/main."
    if (-not $doRebuild) {
        Write-Warning "SkipRebuild set — containers NOT rebuilt (operator override only)."
        exit 0
    }
    Write-Host "REBUILD - code current; running orphan cleanup + full rebuild per deploy policy."
}

if ($vpsHead -eq "MISSING" -or $vpsHead.Length -ne 40) {
    Write-Host "Bootstrap VPS repo (git HEAD unavailable on first probe)..."
    $bootstrap = @"
set -e
sudo mkdir -p $VpsRepo
sudo chown -R ${VpsUser}:${VpsUser} $VpsRepo
if [ ! -d $VpsRepo/.git ]; then
  git clone $GithubRepo $VpsRepo
fi
cd $VpsRepo
git fetch origin main
git reset --hard origin/main
git clean -fd
echo VPS_HEAD=`$(git rev-parse HEAD)
"@
    Invoke-SshScript $bootstrap
    $vpsHead = (Invoke-SshCmd "git -C $VpsRepo rev-parse HEAD").Trim()
}

$bundle = Join-Path $env:TEMP "grok-bot3-sync.bundle"
if ($vpsHead -ne $origin) {
    Write-Host "Creating bundle $vpsHead..$origin ..."
    & git bundle create $bundle "HEAD" "^$vpsHead"
    if (-not (Test-Path $bundle)) {
        Write-Error "Bundle creation failed. VPS=$vpsHead origin=$origin"
    }
    & scp.exe -i $SshKey -o StrictHostKeyChecking=no $bundle "${VpsUser}@${VpsHost}:/tmp/grok-bot3-sync.bundle"
    $remote = @"
set -e
cd $VpsRepo
git fetch /tmp/grok-bot3-sync.bundle HEAD:refs/remotes/bundle/main
git reset --hard bundle/main
git clean -fd
rm -f /tmp/grok-bot3-sync.bundle
echo VPS_HEAD=`$(git rev-parse HEAD)
"@
    Invoke-SshScript $remote
    Remove-Item -Force $bundle -ErrorAction SilentlyContinue
}

if ($doRebuild) {
    $docker = @"
set -e
cd $VpsRepo
python3 scripts/setup-vps-training-env.py
python3 scripts/pulse-babysit/validate-frozen-lock.py $PluginPath/.env || exit 1
cd $PluginPath
docker compose down --remove-orphans
docker compose build
docker compose up -d --force-recreate --remove-orphans
sleep 8
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'hermes-training|hermes-trading-engine'
"@
    Invoke-SshScript $docker
}

$vpsAfter = (Invoke-SshCmd "git -C $VpsRepo rev-parse HEAD").Trim()
if ($vpsAfter -ne $origin) {
    Write-Error "SYNC FAIL after deploy: VPS=$vpsAfter origin=$origin"
}

Write-Host "BOT3 SYNC OK - VPS HEAD matches origin/main ($(Get-ShortSha $origin))."
Write-Host "Dashboard: http://${VpsHost}/dashboard  (Bot 3 Directional)"
Write-Host "TradingView webhook: http://${VpsHost}/webhooks/tradingview"
Write-Host "VERIFY - re-checking VPS HEAD vs origin/main..."
& "$PSScriptRoot\verify-sync-bot3.ps1" -VpsHost $VpsHost -VpsRepo $VpsRepo -SshKey $SshKey
exit $LASTEXITCODE
