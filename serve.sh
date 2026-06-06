#!/bin/bash
cd /home/z/my-project
while true; do
  node lightweight-server.mjs
  echo "Server died, restarting in 2s..."
  sleep 2
done
