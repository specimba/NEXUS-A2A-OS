#!/bin/bash
# NEXUS OS Server Daemon - keeps the server alive
LOGFILE=/home/z/my-project/dev.log
PIDFILE=/home/z/my-project/server.pid

while true; do
  cd /home/z/my-project
  echo "[$(date)] Starting Next.js dev server..." >> "$LOGFILE"
  node node_modules/next/dist/bin/next dev -p 3000 >> "$LOGFILE" 2>&1 &
  SERVER_PID=$!
  echo "$SERVER_PID" > "$PIDFILE"
  wait "$SERVER_PID"
  EXIT_CODE=$?
  echo "[$(date)] Server exited with code $EXIT_CODE, restarting in 3s..." >> "$LOGFILE"
  sleep 3
done
