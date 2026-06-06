#!/bin/bash
# NEXUS-OS Server Keeper
# Runs the Next.js standalone server and auto-restarts on failure

WORKDIR="/home/z/my-project"
SERVER="$WORKDIR/.next/standalone/server.js"
LOGFILE="$WORKDIR/nexus-server.log"
PIDFILE="$WORKDIR/.nexus.pid"
PORT=3000

cd "$WORKDIR"

echo "[$(date)] NEXUS-OS Server Keeper starting..." >> "$LOGFILE"

while true; do
    # Check if server is already running on port 3000
    if curl -s -o /dev/null http://localhost:$PORT --max-time 2 2>/dev/null; then
        echo "[$(date)] Server already running on port $PORT" >> "$LOGFILE"
        sleep 5
        continue
    fi
    
    # Kill any stale processes
    pkill -f "standalone/server.js" 2>/dev/null
    sleep 1
    
    # Start the server
    echo "[$(date)] Starting NEXUS-OS server..." >> "$LOGFILE"
    node "$SERVER" >> "$LOGFILE" 2>&1 &
    SERVER_PID=$!
    echo "$SERVER_PID" > "$PIDFILE"
    
    # Wait for server to be ready
    for i in $(seq 1 10); do
        if curl -s -o /dev/null http://localhost:$PORT --max-time 2 2>/dev/null; then
            echo "[$(date)] Server started successfully (PID: $SERVER_PID)" >> "$LOGFILE"
            break
        fi
        sleep 1
    done
    
    # Wait for server process to exit
    wait $SERVER_PID 2>/dev/null
    EXIT_CODE=$?
    echo "[$(date)] Server exited with code $EXIT_CODE" >> "$LOGFILE"
    
    # Brief delay before restart
    sleep 3
done
