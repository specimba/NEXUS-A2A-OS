#!/bin/bash
# Start script for NEXUS Swarm WebSocket service
# Runs as a persistent foreground process that keeps the service alive

cd /home/z/my-project/mini-services/swarm-ws
exec bun --hot index.ts
