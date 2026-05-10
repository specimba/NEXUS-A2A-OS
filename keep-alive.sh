#!/bin/bash
cd /home/z/my-project
while true; do
    echo "[$(date)] Starting Next.js production server..." >> /home/z/my-project/server.log
    node node_modules/next/dist/bin/next start -p 3000 -H 0.0.0.0 >> /home/z/my-project/server.log 2>&1
    EXIT_CODE=$?
    echo "[$(date)] Server exited with code $EXIT_CODE, restarting in 2s..." >> /home/z/my-project/server.log
    sleep 2
done
