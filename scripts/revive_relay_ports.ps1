# NEXUS Service Auto-Revive (canonical, Windows-native, probe-based)
# Brings every reserved NEXUS port back to life after a PC restart / crash.
# Safe to run repeatedly: only starts a service when its health probe fails.
# See docs/handbook/08_PORT_OWNERSHIP_RULESET.md for the port contract.
param(
    [string]$NexusRoot    = "C:\Users\speci.000\Documents\NEXUS",
    [string]$RelayConfig  = "$env:USERPROFILE\.modelrelay.json",
    [int]$HealthRetries   = 8,
    [int]$HealthDelaySec  = 2,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Continue'
$ModelRelayJs = "$env:APPDATA\npm\node_modules\modelrelay\bin\modelrelay.js"
$Node        = (Get-Command node -ErrorAction SilentlyContinue).Source
$Python      = "$NexusRoot\.venv\Scripts\python.exe"

function Test-Port {
    param([int]$Port, [string]$Path = '/health', [int]$Timeout = 2)
    try {
        $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port$Path" -TimeoutSec $Timeout -ErrorAction Stop
        return ($r.StatusCode -lt 400)
    } catch { return $false }
}

function Wait-Healthy {
    param([int]$Port, [string]$Path, [string]$Label)
    for ($i = 0; $i -lt $HealthRetries; $i++) {
        Start-Sleep -Seconds $HealthDelaySec
        if (Test-Port -Port $Port -Path $Path) {
            Write-Host "[ok] $Label on $Port is healthy" ; return $true
        }
        Write-Host "[...] waiting on $Label ($Port) attempt $($i+1)/$HealthRetries"
    }
    Write-Warning "[fail] $Label on $Port did not become healthy"
    return $false
}

function Start-IfDead {
    param([string]$Label, [int]$Port, [string]$ProbePath, [scriptblock]$Launch)
    if (Test-Port -Port $Port -Path $ProbePath) {
        Write-Host "[skip] $Label already healthy on $Port"
        return $true
    }
    if ($WhatIf) { Write-Host "[whatif] would revive $Label on $Port"; return $false }
    Write-Host "[revive] $Label -> $Port ..."
    try { & $Launch } catch { Write-Warning "launch error: $($_.Exception.Message)" }
    return (Wait-Healthy -Port $Port -Path $ProbePath -Label $Label)
}

# --- 7350: Node ModelRelay primary -------------------------------------------------
$launch7350 = {
    if (-not $Node -or -not (Test-Path $ModelRelayJs)) { Write-Error "node/modelrelay missing"; return }
    Start-Process -NoNewWindow -FilePath $Node `
        -ArgumentList "$ModelRelayJs","--port","7350","--config",$RelayConfig `
        -RedirectStandardOutput "$NexusRoot\logs\modelrelay_7350.out.log" `
        -RedirectStandardError  "$NexusRoot\logs\modelrelay_7350.err.log"
}

# --- 7355: Python ModelRelay fallback (Windows .venv, crash-restart loop) ----------
$bat7355 = "$NexusRoot\scripts\start_python_relay_7355.bat"
$launch7355 = {
    if (-not (Test-Path $Python)) { Write-Error ".venv python missing at $Python"; return }
    Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden `
        -ArgumentList "/c","start `"NEXUS-PythonRelay-7355`" /min cmd /c `"$bat7355`""
}

# --- 7356: static dashboard --------------------------------------------------------
$dashJs = "$NexusRoot\scripts\serve_dashboard_7356.js"
$launch7356 = {
    if (-not $Node -or -not (Test-Path $dashJs)) { Write-Error "dashboard script missing"; return }
    Start-Process -NoNewWindow -FilePath $Node -ArgumentList $dashJs -WorkingDirectory $NexusRoot `
        -RedirectStandardOutput "$NexusRoot\logs\dashboard_7356.out.log" `
        -RedirectStandardError  "$NexusRoot\logs\dashboard_7356.err.log"
}

# --- 7357: God Mode Proxy (Python fastapi between clients and 7350) ----------------
$launch7357 = {
    if (-not (Test-Path $Python)) { Write-Error ".venv python missing at $Python"; return }
    Start-Process -NoNewWindow -FilePath $Python -ArgumentList "-m","nexus_os.relay.god_mode_proxy" `
        -WorkingDirectory $NexusRoot `
        -RedirectStandardOutput "$NexusRoot\logs\god_mode_7357.out.log" `
        -RedirectStandardError  "$NexusRoot\logs\god_mode_7357.err.log"
}

# Ensure logs dir
New-Item -ItemType Directory -Path "$NexusRoot\logs" -Force | Out-Null

# Startup ORDER per port-ownership ruleset: 7350 -> 7352(not here) -> 7356 -> 7355 -> 7357
$r7350 = Start-IfDead -Label 'ModelRelay(7350)'   -Port 7350 -ProbePath '/'       -Launch $launch7350
$r7356 = Start-IfDead -Label 'Dashboard(7356)'    -Port 7356 -ProbePath '/'       -Launch $launch7356
$r7355 = Start-IfDead -Label 'PythonRelay(7355)'  -Port 7355 -ProbePath '/health' -Launch $launch7355
$r7357 = Start-IfDead -Label 'GodModeProxy(7357)'-Port 7357 -ProbePath '/health' -Launch $launch7357

Write-Host ""
Write-Host "=== revive report ==="
$report = [ordered]@{
    '7350_modelrelay' = $r7350
    '7355_pythonrelay'= $r7355
    '7356_dashboard'  = $r7356
    '7357_godmode'    = $r7357
}
$report.GetEnumerator() | ForEach-Object { Write-Host ("{0,-18} {1}" -f $_.Key, $(if($_.Value){'UP'}else{'DOWN'})) }

# Exit non-zero only if a *core* relay (7350 or 7355) failed — dashboard/godmode are secondary
if (-not ($r7350 -or $r7355)) { exit 1 } else { exit 0 }
