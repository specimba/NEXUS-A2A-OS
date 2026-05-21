#!/bin/bash
# NEXUS OS Persistent Server Daemon
# Runs the standalone production server with auto-restart
cd /home/z/my-project
while true; do
  PORT=3000 node .next/standalone/server.js 2>&1 | tee -a /tmp/nexus-server.log
  echo "[$(date)] Server exited, restarting in 2s..." >> /tmp/nexus-server.log
  sleep 2
done
