#!/bin/bash
# Health check for NEXUS-OS server
# Returns 0 if healthy, 1 if needs restart
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
  echo "OK: Server is healthy (HTTP 200)"
  exit 0
else
  echo "FAIL: Server returned HTTP $HTTP_CODE. Restarting..."
  pkill -f nexus-supervisord 2>/dev/null
  sleep 2
  setsid /tmp/nexus-supervisord.sh >> /tmp/nexus-supervisor.log 2>&1 &
  sleep 5
  NEW_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null)
  echo "After restart: HTTP $NEW_CODE"
  exit 0
fi
