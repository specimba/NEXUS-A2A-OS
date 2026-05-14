#!/bin/bash
cd /home/z/my-project
while true; do
  node lightweight-server.mjs 2>&1
  sleep 1
done
