# Single-line-safe entry: preflight only (no multi-paste required).
#   .\scripts\run_a2a_preflight_only.ps1
param([int]$Port = 9224)
& "$PSScriptRoot\watch_lane_stack.ps1" -Port $Port
