#!/bin/bash
while true; do
  cd /home/z/my-project
  bun .next/standalone/server.js >> /home/z/my-project/dev.log 2>&1 &
  PID=$!
  echo "[$(date)] Started server PID=$PID"
  # Wait for it to die
  while kill -0 $PID 2>/dev/null; do
    sleep 2
  done
  echo "[$(date)] Server died, restarting in 3s..."
  sleep 3
done
