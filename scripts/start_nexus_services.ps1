param(
    [switch]$No7350,
    [switch]$No7355,
    [switch]$No7356,
    [switch]$No7357
)

$Root = "C:\Users\speci.000\Documents\NEXUS"
$NodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
$Pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $Pwsh) { $Pwsh = (Get-Command powershell -ErrorAction SilentlyContinue).Source }
$ModelRelayRuntime = "$Root\scripts\modelrelay_runtime.ps1"
$Python = "$Root\.venv\Scripts\python.exe"

if (-not $NodeExe) { Write-Error "node not found"; exit 1 }
if (-not $Pwsh) { Write-Error "PowerShell not found"; exit 1 }
if (-not (Test-Path $ModelRelayRuntime)) { Write-Error "repo ModelRelay runtime missing"; exit 1 }

$windows = @()

function Start-Window {
    param($Title, $FilePath, $Args, $Port, $CheckPath = '/')
    $existing = $null
    try { $existing = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port$CheckPath" -TimeoutSec 2 -ErrorAction Stop } catch {}
    if ($existing -and $existing.StatusCode -lt 400) {
        Write-Host "[OK] $Title already running on $Port ($($existing.StatusCode))"
        return
    }
    $psi = @{
        FilePath = 'cmd.exe'
        ArgumentList = @('/c', 'start', $Title, '/min', $FilePath, $Args)
        WindowStyle = 'Hidden'
        PassThru = $true
    }
    Start-Process @psi | Out-Null
    Write-Host "[STARTED] $Title on $Port"
}

# 7350 — repo-owned governed ModelRelay
if (-not $No7350) {
    $relayHealthy = $false
    try { $relayHealthy = (Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:7350/' -TimeoutSec 2 -ErrorAction Stop).StatusCode -lt 400 } catch {}
    if ($relayHealthy) {
        Write-Host '[OK] NEXUS-ModelRelay-7350 already running'
    } else {
        Start-Process -FilePath $Pwsh -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$ModelRelayRuntime,'-Port','7350','-ConfigPath',"$env:USERPROFILE\.modelrelay.json",'-Bind','0.0.0.0')
        Write-Host '[STARTED] governed ModelRelay on 7350'
    }
}

# 7355 — Python Relay
if (-not $No7355) {
    $batPath = "$Root\scripts\start_python_relay_7355.bat"
    if (Test-Path $batPath) {
        Start-Process -FilePath 'cmd.exe' -ArgumentList "/c start `"NEXUS-PythonRelay-7355`" /min cmd /c $batPath" -WindowStyle Hidden
        Write-Host "[STARTED] Python Relay on 7355"
    }
}

# 7356 — Dashboard
if (-not $No7356) {
    Start-Window -Title 'NEXUS-Dashboard-7356' -FilePath $NodeExe -Args "$Root\scripts\serve_dashboard_7356.js" -Port 7356
}

# 7357 — God Mode Proxy
if (-not $No7357) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList "/c start `"NEXUS-GodMode-7357`" /min cmd /c $Python -m nexus_os.relay.god_mode_proxy" -WindowStyle Hidden
    Write-Host "[STARTED] God Mode Proxy on 7357"
}

Write-Host ""
Write-Host "=== Verifying ==="
Start-Sleep -Seconds 3
@(7350,7355,7356,7357) | ForEach-Object {
    $p = $_
    try {
        $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:${p}/" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "[$($r.StatusCode)] Port $p is UP"
    } catch {
        Write-Host "[DOWN] Port $p unreachable"
    }
}
Write-Host "=== Done ==="
Write-Host "Open http://localhost:7356/dashboard.html for dashboard"
