# NEXUS 4-hour CLI model sync — keeps every CLI's model config current
# with the live arsenal (operator requirement 2026-07-02: "all CLIs have
# to reach models dynamically, updated per 4 hours").
#
# Fan-out (via nexusctl model-sync): opencode, kilocode, cline, hermes
# (WSL2 reads the same Windows config), mimo, nexusctl itself.
# Devin has no local config file to write — it consumes the relay
# endpoint directly.
#
# Register (one-time, as the logged-in user):
#   schtasks /Create /TN "NexusModelSync4h" /SC HOURLY /MO 4 ^
#     /TR "powershell -NoProfile -File C:\Users\speci.000\Documents\NEXUS\scripts\nexus_model_sync_4h.ps1" /F
$ErrorActionPreference = "Continue"
$repo = "C:\Users\speci.000\Documents\NEXUS"
$log = Join-Path $repo "logs\model_sync_4h.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content $log "[$stamp] model-sync run starting"

Set-Location $repo
# 1. Refresh live model state from the relays and fan out to every CLI config.
python -m nexusctl model-sync --refresh 2>&1 | Select-Object -Last 5 | ForEach-Object { Add-Content $log "  $_" }

# 2. Refresh the registry health sidecar (listing-only; no chat probes on
#    the scheduled path — quota-fragile providers stay untouched).
python -m nexusctl models verify --no-chat-probe 2>&1 | Select-Object -Last 3 | ForEach-Object { Add-Content $log "  $_" }

Add-Content $log "[$stamp] model-sync run finished"
