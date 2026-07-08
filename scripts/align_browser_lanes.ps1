# Align registry lane URLs only — no window restore (no minimize twitch).
param([int]$Port = 9224, [switch]$SkipEnsure)

$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo
if (-not $SkipEnsure) {
    & "$Repo\scripts\ensure_lane_cdp.ps1" -Port $Port
}
node "$Repo\tools\browser_ai_supervisor\open_or_navigate_lane.mjs" --port $Port --all
Write-Host (ConvertTo-Json @{ status = "LANES_ALIGNED"; port = $Port })