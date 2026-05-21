#!/bin/bash
cd /home/z/my-project

# Ensure build exists
if [ ! -f ".next/standalone/server.js" ]; then
    echo "No standalone build found, building..."
    npx next build
    mkdir -p .next/standalone/.next
    cp -r .next/static .next/standalone/.next/
    cp -r public .next/standalone/ 2>/dev/null
fi

# Run the standalone server (low memory footprint ~120MB)
exec node .next/standalone/server.js
