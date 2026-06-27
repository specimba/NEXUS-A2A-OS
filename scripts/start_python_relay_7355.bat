@echo off
setlocal
cd /d C:\Users\speci.000\Documents\NEXUS
set MODELRELAY_CONFIG=%USERPROFILE%\.modelrelay.json
set RELAY_PORT=7355
set RELAY_HEALTH_INTERVAL=0

:loop
echo [%date% %time%] Starting NEXUS Python relay on %RELAY_PORT%...
"C:\Users\speci.000\Documents\NEXUS\.venv\Scripts\python.exe" -m nexus_os.relay.model_relay >> logs\python_relay_7355.out.log 2>> logs\python_relay_7355.err.log
echo [%date% %time%] Python relay exited. Retry in 5s.
timeout /t 5 /nobreak >NUL
goto loop
