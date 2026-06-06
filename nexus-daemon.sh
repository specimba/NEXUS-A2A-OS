#!/bin/bash
WORKDIR="/home/z/my-project"
LOGFILE="$WORKDIR/nexus-server.log"
cd "$WORKDIR"

while true; do
    echo "[$(date)] Starting NEXUS-OS server..." >> "$LOGFILE"
    node .next/standalone/server.js >> "$LOGFILE" 2>&1
    echo "[$(date)] Server exited, restarting in 3s..." >> "$LOGFILE"
    sleep 3
done
