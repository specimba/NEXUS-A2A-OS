@echo off
setlocal
REM Start/check the NEXUS guard-plane ngrok tunnel.
REM Credentials stay in the user-local ngrok config, never in this repo script.
REM Set NEXUS_NGROK_RESTART=1 if you explicitly want to kill existing ngrok processes.

set "TUNNEL_NAME=guard-plane"
set "HEALTH_PATH=/v1/health"

if "%NEXUS_NGROK_RESTART%"=="1" (
  echo Restart requested. Stopping existing ngrok processes...
  taskkill /f /im ngrok.exe >nul 2>&1
  timeout /t 3 /nobreak >nul
) else (
  echo Non-disruptive mode. Existing ngrok processes will not be killed.
)

echo Starting guard-plane tunnel...
start "" /b ngrok start %TUNNEL_NAME% --log=stdout --log-level=info
echo Checking tunnel...
timeout /t 8 /nobreak >nul
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; try { $tunnels = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 5; $tunnel = $tunnels.tunnels | Where-Object { $_.name -eq '%TUNNEL_NAME%' } | Select-Object -First 1; if (-not $tunnel) { throw 'Named tunnel not found in local ngrok API.' }; $url = [string]$tunnel.public_url; Write-Host ('PUBLIC_URL: ' + $url); $r = Invoke-WebRequest -Uri ($url + '%HEALTH_PATH%') -TimeoutSec 10 -UseBasicParsing; Write-Host ('HEALTH: ' + $r.StatusCode) } catch { Write-Host ('Tunnel not ready: ' + $_.Exception.Message); exit 1 }"
echo Done. PID:
powershell -NoProfile -Command "Get-Process ngrok -ErrorAction SilentlyContinue | Select-Object Id, ProcessName"
