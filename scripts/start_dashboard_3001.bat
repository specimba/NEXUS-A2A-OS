@echo off
REM Next.js dashboard launcher (port 3001). All output -> log file (no console noise).
REM Launched detached/hidden by scripts\start_nexus_gateway.ps1 so it survives terminal close.
setlocal
cd /d "C:\Users\speci.000\Documents\NEXUS"
set "LOG=C:\Users\speci.000\Documents\NEXUS\logs\gateway\dashboard_3001.log"
if not exist "logs\gateway" mkdir "logs\gateway"
call npx next dev -p 3001 > "%LOG%" 2>&1
endlocal
