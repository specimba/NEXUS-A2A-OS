#!/bin/bash
# NEXUS OS Dev Server - Persistent Runner
cd /home/z/my-project

# Kill any existing Next.js processes
pkill -f "next dev -p 3000" 2>/dev/null || true
sleep 1

# Start the dev server
NODE_OPTIONS='--max-old-space-size=4096' exec node node_modules/.bin/next dev -p 3000 >> dev.log 2>&1
