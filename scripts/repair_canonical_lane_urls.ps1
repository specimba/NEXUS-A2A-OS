# Re-navigate registry lanes to canonical URLs (fixes wrong Gemini / stale z.ai tabs).
param([int]$Port = 9224)

$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo
& "$Repo\scripts\ensure_lane_cdp.ps1" -Port $Port | Out-Null
node "$Repo\tools\browser_ai_supervisor\open_or_navigate_lane.mjs" --port $Port --all