#!/bin/bash
# Tailscale Entry Point for NEXUS OS
# Purpose: Initialize Tailscale networking for secure agent communication

set -e

echo "[NEXUS Tailscale] Starting Tailscale initialization..."

# Environment variables
TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY:-}
AGENT_ID=${AGENT_ID:-nexus-agent-default}
TAILSCALE_STATE_DIR=${TAILSCALE_STATE_DIR:-/var/lib/tailscale}
NEXUS_HOSTNAME=${NEXUS_HOSTNAME:-nexus-${AGENT_ID}}
ADVERTISE_ROUTES=${ADVERTISE_ROUTES:-}
ACCEPT_ROUTES=${ACCEPT_ROUTES:-}
EXIT_NODE=${EXIT_NODE:-}

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to cleanup on exit
cleanup() {
    log "Shutting down Tailscale..."
    tailscale down || true
    log "Tailscale shutdown complete"
}

trap cleanup EXIT TERM INT

# Validate required environment variables
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    log "ERROR: TAILSCALE_AUTHKEY environment variable is required"
    exit 1
fi

# Start Tailscaled in background
log "Starting tailscaled daemon..."
tailscaled --state=$TAILSCALE_STATE_DIR/tailscaled.state \
    --socket=/var/run/tailscale/tailscaled.sock &
TAILSCALED_PID=$!

# Wait for tailscaled to be ready
log "Waiting for tailscaled to start..."
sleep 2

# Check if tailscaled is running
if ! kill -0 $TAILSCALED_PID 2>/dev/null; then
    log "ERROR: tailscaled failed to start"
    exit 1
fi

# Authenticate with Tailscale
log "Authenticating with Tailscale as $NEXUS_HOSTNAME..."
tailscale up \
    --authkey="$TAILSCALE_AUTHKEY" \
    --hostname="$NEXUS_HOSTNAME" \
    --accept-routes=${ACCEPT_ROUTES:-false} \
    --advertise-routes=${ADVERTISE_ROUTES:-""} \
    --reset

# Wait for connection
log "Waiting for Tailscale connection..."
for i in {1..30}; do
    if tailscale status > /dev/null 2>&1; then
        log "Tailscale connection established"
        break
    fi
    if [ $i -eq 30 ]; then
        log "ERROR: Tailscale connection timeout"
        exit 1
    fi
    sleep 1
done

# Configure exit node if specified
if [ -n "$EXIT_NODE" ]; then
    log "Configuring exit node: $EXIT_NODE"
    tailscale up --exit-node="$EXIT_NODE" || \
        log "WARNING: Failed to configure exit node"
fi

# Display Tailscale status
log "Tailscale Status:"
tailscale status

# Get Tailscale IP addresses
TAILSCALE_IPS=$(tailscale ip -4)
log "Tailscale IPv4 addresses: $TAILSCALE_IPS"

# Export Tailscale IP for NEXUS OS components
export TAILSCALE_IP=$(echo $TAILSCALE_IPS | awk '{print $1}')
export TAILSCALE_IPV4=$TAILSCALE_IP
export NEXUS_NETWORKING="tailscale"

# Create NEXUS networking configuration
mkdir -p /etc/nexus
cat > /etc/nexus/networking.conf <<EOF
NEXUS_NETWORKING_PROVIDER=tailscale
TAILSCALE_IP=$TAILSCALE_IP
TAILSCALE_HOSTNAME=$NEXUS_HOSTNAME
TAILSCALE_AUTHENTICATED=true
NEXUS_AGENT_ID=$AGENT_ID
EOF

log "NEXUS networking configuration written to /etc/nexus/networking.conf"

# Start NEXUS OS components if requested
if [ "$START_NEXUS" = "true" ]; then
    log "Starting NEXUS OS components..."
    
    # Start Bridge Server
    if [ "$START_BRIDGE" = "true" ]; then
        log "Starting NEXUS Bridge Server on port 7352..."
        cd /app/nexus_os
        python -m nexus_os.bridge.server &
        BRIDGE_PID=$!
        echo $BRIDGE_PID > /var/run/nexus/bridge.pid
    fi
    
    # Start TWAVE Wrapper
    if [ "$START_TWAVE" = "true" ]; then
        log "Starting NEXUS TWAVE Wrapper on port 7353..."
        cd /app/nexus_os
        python -m nexus_os.twave.wrapper &
        TWAVE_PID=$!
        echo $TWAVE_PID > /var/run/nexus/twave.pid
    fi
    
    # Start WebSocket Service
    if [ "$START_WEBSOCKET" = "true" ]; then
        log "Starting NEXUS WebSocket Service on port 3003..."
        cd /app/nexus_os
        python -m nexus_os.swarm.websocket &
        WEBSOCKET_PID=$!
        echo $WEBSOCKET_PID > /var/run/nexus/websocket.pid
    fi
    
    log "All requested NEXUS components started"
else
    log "NEXUS OS components not started (set START_NEXUS=true to enable)"
fi

# Keep container running
log "Tailscale networking active, waiting for signals..."
wait $TAILSCALED_PID