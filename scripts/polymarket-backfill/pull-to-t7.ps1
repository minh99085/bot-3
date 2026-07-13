# Copy Polymarket training data from Bot 3 VPS to your Samsung T7.
# Run in PowerShell on your laptop when the download is finished.
param(
    [string]$Dest = "D:\polymarket-training",
    [string]$VpsHost = "207.246.96.45",
    [string]$SshKey = "$env:USERPROFILE\.ssh\bot3_cloud_agent"
)

$Remote = "/var/lib/docker/volumes/bot3-vps_hte_data/_data/polymarket-training"
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Pulling from VPS $VpsHost ..."
scp -i $SshKey -o StrictHostKeyChecking=no -r "root@${VpsHost}:${Remote}/" $Dest
Write-Host "Done. Data is at $Dest"
Write-Host "Key files:"
Write-Host "  curated\windows.csv"
Write-Host "  curated\trades.csv"
Write-Host "  curated\prices.csv"
Write-Host "  curated\synthetic_ledger.json"
