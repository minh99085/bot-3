# One-time: grant this cloud agent SSH access to Bot-1 VPS.
# Run from laptop (has id_ed25519 authorized on Bot-1).
#
# After this, cloud agents can finish lessons transfer autonomously.
[CmdletBinding()]
param(
    [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$VpsHost = "45.32.227.242",
    [string]$VpsUser = "linuxuser"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$PubFile = Join-Path $RepoRoot "scripts\keys\bot3-cloud-agent.pub"

if (-not (Test-Path $PubFile)) {
    throw "Missing $PubFile — git pull origin main first."
}
if (-not (Test-Path $SshKey)) {
    throw "Missing Bot-1 private key: $SshKey"
}

$pub = (Get-Content $PubFile -Raw).Trim()
$escaped = $pub.Replace("'", "'\''")

Write-Host "Granting cloud-agent SSH on ${VpsUser}@${VpsHost}..."
& ssh.exe -i $SshKey -o ConnectTimeout=20 -o StrictHostKeyChecking=no "${VpsUser}@${VpsHost}" @"
mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qF 'bot3-cloud-agent' ~/.ssh/authorized_keys 2>/dev/null || echo '$escaped' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
# If SSH is IP-allowlisted, also ensure cloud egress can reach :22 (firewall/ufw/Vultr).
grep bot3-cloud-agent ~/.ssh/authorized_keys
echo BOT1_GRANT_OK
"@
if ($LASTEXITCODE -ne 0) { throw "Failed to grant cloud-agent key on Bot-1" }

Write-Host "Done. If SSH still resets from cloud, open port 22 for Cursor cloud egress (not just your laptop IP)."
