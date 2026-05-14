#!/bin/bash
# Check if server is running on port 3000
if ! curl -s -o /dev/null -w '' http://localhost:3000/ 2>/dev/null; then
  echo "[$(date)] Server not responding, restarting..." >> /home/z/my-project/keep-alive.log
  # Kill any stale processes
  pkill -f "server.js" 2>/dev/null
  sleep 1
  # Start server
  cd /home/z/my-project
  NODE_OPTIONS="--max-old-space-size=512" HOSTNAME="0.0.0.0" PORT=3000 nohup node .next/standalone/server.js > /home/z/my-project/dev.log 2>&1 &
  echo "[$(date)] Server restarted with PID $!" >> /home/z/my-project/keep-alive.log
fi
