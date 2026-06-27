# NEXUS Gateway Starter — one command to bring up the FULL stack in background.
# All services launch DETACHED (hidden windows / Start-Process), so closing this
# terminal does NOT kill them. Each writes it own log under logs\gateway\.
# Re-run any time; it skips services already healthy.
#
# Run in your ADMIN terminal:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_nexus_gateway.ps1
# Add to Windows startup (auto-start after reboot):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_nexus_autostart.ps1
#
# Service map (see docs/handbook/08_PORT_OWNERSHIP_RULESET.md):
#   7350 Node ModelRelay primary   7355 Python relay fallback   7357 God Mode proxy
#   7356 static dashboard UI        7354 Grok MCP bridge         3001 Next.js dashboard
#   9224 Chrome CDP (Grok lane; persistent profile, log in ONCE)
param(
    [switch]$SkipChrome,      # skip launching the dedicated Grok Chrome
    [switch]$SkipDashboard,   # skip launching the Next.js dashboard (3001)
    [switch]$SkipBridge,       # skip the Grok MCP bridge (7354)
    [int]$ProbeTimeoutSec = 20
)

$ErrorActionPreference = 'Continue'
$Root        = 'C:\Users\speci.000\Documents\NEXUS'
$Logs        = Join-Path $Root 'logs\gateway'
$ModelRelayJs= "$env:APPDATA\npm\node_modules\modelrelay\bin\modelrelay.js"
$Node        = (Get-Command node -ErrorAction SilentlyContinue).Source
$Python      = "$Root\.venv\Scripts\python.exe"
$DashBat7355 = "$Root\scripts\start_python_relay_7355.bat"
$DashJs7356  = "$Root\scripts\serve_dashboard_7356.js"
$CdpScript   = "$Root\scripts\start_grok_cdp_9224.ps1"
$BridgeScript= "$Root\tools\browser_ai_mcp\start_grok_mcp_v2.ps1"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Test-Port([int]$Port,[string]$Path='/health',[int]$Timeout=2){ try{ $r=Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port$Path" -TimeoutSec $Timeout -ErrorAction Stop; return $r.StatusCode -lt 400 }catch{ return $false } }

# Fast TCP-listening probe: true if something is accepting connections on the port.
# Use this for dev servers (e.g. Next.js) whose HTTP root may cold-compile or
# redirect while the server is in fact already up and listening.
function Test-Listening([int]$Port,[int]$Ms=800){
    $c = $null
    try { $c = New-Object System.Net.Sockets.TcpClient; $iar = $c.BeginConnect('127.0.0.1',$Port,$null,$null); $ok = $iar.AsyncWaitHandle.WaitOne($Ms,$false); if ($ok -and $c.Connected) { return $true }; return $false }
    catch { return $false }
    finally { if ($c) { try { $c.Close() } catch {} } }
}

function Start-IfDead([string]$Label,[int]$Port,[string]$ProbePath,[scriptblock]$Launch){
    if (Test-Port $Port $ProbePath) { Write-Host "[skip] $Label ($Port) already up"; return $true }
    if (Test-Listening $Port) { Write-Host "[skip] $Label ($Port) already listening"; return $true }
    Write-Host "[start] $Label ($Port)..."
    try { & $Launch } catch { Write-Warning "  launch error: $($_.Exception.Message)" }
    Start-Sleep -Seconds 3
    if (Test-Port $Port $ProbePath) { return $true }
    return (Test-Listening $Port)
}

# 7350 Node ModelRelay
$r0 = Start-IfDead 'Node ModelRelay' 7350 '/' {
    Start-Process -NoNewWindow -FilePath $Node -ArgumentList "$ModelRelayJs","--port","7350","--config","$env:USERPROFILE\.modelrelay.json" -RedirectStandardOutput "$Logs\modelrelay_7350.out.log" -RedirectStandardError "$Logs\modelrelay_7350.err.log"
}

# 7355 Python relay (detached batch with built-in retry loop)
$r5 = Start-IfDead 'Python relay' 7355 '/health' {
    Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden -ArgumentList "/c","start `"NEXUS-PythonRelay-7355`" /min cmd /c `"$DashBat7355`""
}

# 7357 God Mode proxy
$r7 = Start-IfDead 'God Mode proxy' 7357 '/health' {
    Start-Process -NoNewWindow -FilePath $Python -ArgumentList '-m','nexus_os.relay.god_mode_proxy' -WorkingDirectory $Root -RedirectStandardOutput "$Logs\godmode_7357.out.log" -RedirectStandardError "$Logs\godmode_7357.err.log"
}

# 7356 static dashboard UI
$r6 = Start-IfDead 'Static dashboard UI' 7356 '/' {
    Start-Process -NoNewWindow -FilePath $Node -ArgumentList $DashJs7356 -WorkingDirectory $Root -RedirectStandardOutput "$Logs\dashboard_7356.out.log" -RedirectStandardError "$Logs\dashboard_7356.err.log"
}

# 7354 Grok MCP bridge (optional)
if ($SkipBridge) { $r4 = $true } else {
    $r4 = Start-IfDead 'Grok MCP bridge' 7354 '/health' {
        if (Test-Path $BridgeScript) { Start-Process -NoNewWindow -FilePath 'powershell' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$BridgeScript -RedirectStandardOutput "$Logs\grokbridge_7354.out.log" -RedirectStandardError "$Logs\grokbridge_7354.err.log" }
        else { Write-Warning '  grok bridge launcher missing' }
    }
}

# 3001 Next.js dashboard — detached hidden batch so it survives terminal close (no console noise)
$DashBat3001 = "$Root\scripts\start_dashboard_3001.bat"
if ($SkipDashboard) { $r1 = $true } else {
    if (Test-Port 3001 '/api/nexusclaw/status' 3) { Write-Host "[skip] Next.js dashboard (3001) already up"; $r1 = $true }
    elseif (Test-Listening 3001) { Write-Host "[skip] Next.js dashboard (3001) already listening"; $r1 = $true }
    else {
        Write-Host "[start] Next.js dashboard (3001)..."
        Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden -ArgumentList "/c","`"$DashBat3001`""
        # wait up to ~25s for the dev server to bind (cold Turbopack compile first run)
        $r1 = $false
        for ($i=0; $i -lt 25; $i++) { Start-Sleep -Seconds 1; if (Test-Listening 3001) { $r1 = $true; break } }
        if ($r1 -and (Test-Port 3001 '/api/nexusclaw/status' $ProbeTimeoutSec)) { Write-Host "  api route ready" }
    }
}

# 9224 Grok-lane Chrome (persistent dedicated profile; log in to Grok ONCE, then survives all restarts)
if ($SkipChrome) { $rc = $true } else {
    $rc = Start-IfDead 'Grok CDP Chrome' 9224 '/json/version' {
        if (Test-Path $CdpScript) { & $CdpScript } else { Write-Warning '  CDP launcher missing' }
    }
    if (-not $rc) { $rc = Test-Port 9224 '/json/version' $ProbeTimeoutSec }
}

Write-Host ""
Write-Host "=== NEXUS Gateway status ==="
$report = [ordered]@{ '7350 relay'=$r0; '7355 relay'=$r5; '7357 godmode'=$r7; '7356 dash_ui'=$r6; '7354 grok_bridge'=$r4; '3001 dashboard'=$r1; '9224 cdp'=$rc }
foreach ($k in $report.Keys) { Write-Host ("  {0,-18} {1}" -f $k, $(if($report[$k]){'UP'}else{'DOWN'})) }
Write-Host ""
Write-Host "Verify from any shell:  nexusctl grok-lane doctor"
Write-Host "Auto-start on reboot:   powershell -File scripts\install_nexus_autostart.ps1"
Write-Host "Logs:                    $Logs"
$coreOk = $r0 -and $r5 -and $r7
if ($coreOk) { exit 0 } else { exit 1 }
