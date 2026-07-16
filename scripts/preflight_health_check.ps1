param([string]$LogPath = "C:\Users\speci.000\Downloads\NEXUSlogs\preflight_$(Get-Date -Format 'yyyyMMdd').log")
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
function Write-Log { param([string]$M) $l="$(Get-Date -Format 'HH:mm:ss') $M"; Write-Output $l; Add-Content $LogPath $l }
Write-Log "=== NEXUS Preflight Health Check ==="
# Port check
foreach ($p in 7350,7352,7354,7355,7356,7357,9224) {
    try { $r=Invoke-WebRequest -Uri "http://127.0.0.1:$p/health" -TimeoutSec 3 -UseBasicParsing; Write-Log "port $p : OK" } catch { Write-Log "port $p : FAIL ($($_.Exception.Message))" }
}
# GitHub tick check
try {
    $t=(gh auth token).Trim()
    $j=Invoke-RestMethod -Uri "https://api.github.com/repos/specimba/NEXUS_discovery_GPU/contents/reports/session4/a800/LATEST.json" -Headers @{"Authorization"="Bearer $t";"Accept"="application/vnd.github.raw";"User-Agent"="neflight"}
    Write-Log "A800: tick=$($j.tick) stamp=$($j.stamp) mode=$($j.mode)"
} catch { Write-Log "A800 check: FAIL ($($_.Exception.Message))" }
# Calm process check
$calm=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "_a800_calm" }).Count
Write-Log "calm processes: $calm"
Write-Log "=== Preflight Complete ==="
