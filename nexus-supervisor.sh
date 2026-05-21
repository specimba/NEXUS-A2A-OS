#!/bin/bash
# Check if server is running, restart if not
if ! curl -s -o /dev/null -w "" http://localhost:3000 --max-time 3 2>/dev/null; then
    echo "[$(date)] Server not responding, starting..." >> /home/z/my-project/supervisor.log
    cd /home/z/my-project
    pkill -f "standalone/server.js" 2>/dev/null
    sleep 1
    # Start with nohup and disown
    nohup node .next/standalone/server.js >> /home/z/my-project/supervisor.log 2>&1 &
    disown
    sleep 2
    if curl -s -o /dev/null http://localhost:3000 --max-time 3 2>/dev/null; then
        echo "[$(date)] Server started successfully" >> /home/z/my-project/supervisor.log
    else
        echo "[$(date)] Server failed to start" >> /home/z/my-project/supervisor.log
    fi
else
    echo "[$(date)] Server is running" >> /home/z/my-project/supervisor.log
fi
