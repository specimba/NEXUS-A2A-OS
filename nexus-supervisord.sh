#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# NEXUS-OS v3.1 — Persistent Server Supervisor
# ═══════════════════════════════════════════════════════════════════
# This script MUST survive:
#   1. Bash session termination (double-fork + setsid)
#   2. Server crashes (auto-restart with backoff)
#   3. Sandbox reboots (needs crontab @reboot or init hook)
#   4. OOM kills (memory monitoring)
#
# Architecture:
#   supervisord.sh → spawns server in loop
#   PID file at /tmp/nexus-server.pid for external control
#   Log file at /tmp/nexus-supervisor.log
#   Health check endpoint monitoring
# ═══════════════════════════════════════════════════════════════════

PROJECT_DIR="/home/z/my-project"
SERVER_CMD="node .next/standalone/server.js"
PORT=3000
HOSTNAME="0.0.0.0"
PID_FILE="/tmp/nexus-server.pid"
SUPERVISOR_PID_FILE="/tmp/nexus-supervisor.pid"
LOG_FILE="/tmp/nexus-supervisor.log"
HEALTH_URL="http://localhost:${PORT}/"
MAX_RESTARTS=10
RESTART_INTERVAL=60   # Reset restart counter after this many seconds of uptime
BACKOFF_BASE=2        # Initial backoff in seconds
BACKOFF_MAX=30        # Max backoff in seconds

# ─── Logging ─────────────────────────────────────────────────────
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [supervisor] $*" >> "$LOG_FILE"
}

# ─── Pre-flight checks ───────────────────────────────────────────
preflight() {
  log "Running pre-flight checks..."

  # Check if project directory exists
  if [ ! -d "$PROJECT_DIR" ]; then
    log "FATAL: Project directory $PROJECT_DIR not found"
    exit 1
  fi

  # Check if standalone server exists
  if [ ! -f "$PROJECT_DIR/.next/standalone/server.js" ]; then
    log "FATAL: Standalone server not found. Run 'bun run build' first."
    exit 1
  fi

  # Check if static files are synced
  if [ ! -d "$PROJECT_DIR/.next/standalone/.next/static" ]; then
    log "WARNING: Static files not synced. Copying..."
    cp -r "$PROJECT_DIR/.next/static" "$PROJECT_DIR/.next/standalone/.next/" 2>/dev/null
    cp -r "$PROJECT_DIR/public" "$PROJECT_DIR/.next/standalone/" 2>/dev/null
  fi

  # Kill any existing server on the same port
  local existing_pid
  existing_pid=$(lsof -ti :$PORT 2>/dev/null)
  if [ -n "$existing_pid" ]; then
    log "Port $PORT is in use by PID $existing_pid. Killing..."
    kill -9 $existing_pid 2>/dev/null
    sleep 2
  fi

  # Kill any existing supervisor
  if [ -f "$SUPERVISOR_PID_FILE" ]; then
    local old_sup_pid
    old_sup_pid=$(cat "$SUPERVISOR_PID_FILE" 2>/dev/null)
    if [ -n "$old_sup_pid" ] && kill -0 "$old_sup_pid" 2>/dev/null; then
      log "Killing existing supervisor PID $old_sup_pid"
      kill -9 "$old_sup_pid" 2>/dev/null
      sleep 1
    fi
    rm -f "$SUPERVISOR_PID_FILE"
  fi

  # Write our PID
  echo $$ > "$SUPERVISOR_PID_FILE"
  log "Supervisor started with PID $$"
}

# ─── Health check ─────────────────────────────────────────────────
health_check() {
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null)
  if [ "$http_code" = "200" ]; then
    return 0
  else
    return 1
  fi
}

# ─── Main supervisor loop ────────────────────────────────────────
supervise() {
  local restart_count=0
  local last_restart_time=0
  local current_backoff=$BACKOFF_BASE

  while true; do
    log "Starting NEXUS-OS server (attempt $((restart_count + 1))/$MAX_RESTARTS)..."

    cd "$PROJECT_DIR"

    # Start the server
    PORT=$PORT HOSTNAME=$HOSTNAME $SERVER_CMD >> "$LOG_FILE" 2>&1 &
    local server_pid=$!
    echo "$server_pid" > "$PID_FILE"

    log "Server started with PID $server_pid"

    # Wait for server to be ready (up to 15 seconds)
    local ready=0
    for i in $(seq 1 15); do
      sleep 1
      if health_check; then
        ready=1
        log "Server is ready (health check passed after ${i}s)"
        break
      fi
    done

    if [ $ready -eq 0 ]; then
      log "WARNING: Server started but health check failed after 15s"
    fi

    # Wait for the server process to exit
    wait "$server_pid" 2>/dev/null
    local exit_code=$?
    log "Server exited with code $exit_code"

    # Clean up PID file
    rm -f "$PID_FILE"

    # Check if we should restart
    local now
    now=$(date +%s)
    local uptime=$((now - last_restart_time))

    # Reset restart counter if server ran for more than RESTART_INTERVAL
    if [ $uptime -gt $RESTART_INTERVAL ] && [ $last_restart_time -gt 0 ]; then
      restart_count=0
      current_backoff=$BACKOFF_BASE
      log "Server ran for ${uptime}s — resetting restart counter"
    fi

    restart_count=$((restart_count + 1))
    last_restart_time=$now

    if [ $restart_count -ge $MAX_RESTARTS ]; then
      log "FATAL: Max restarts ($MAX_RESTARTS) reached. Waiting 120s before retry..."
      sleep 120
      restart_count=0
      current_backoff=$BACKOFF_BASE
      continue
    fi

    # Exponential backoff
    log "Restarting in ${current_backoff}s (backoff)..."
    sleep "$current_backoff"
    current_backoff=$((current_backoff * 2))
    if [ $current_backoff -gt $BACKOFF_MAX ]; then
      current_backoff=$BACKOFF_MAX
    fi
  done
}

# ─── Signal handlers ─────────────────────────────────────────────
cleanup() {
  log "Supervisor shutting down..."
  local server_pid
  server_pid=$(cat "$PID_FILE" 2>/dev/null)
  if [ -n "$server_pid" ]; then
    log "Stopping server PID $server_pid..."
    kill "$server_pid" 2>/dev/null
    wait "$server_pid" 2>/dev/null
  fi
  rm -f "$PID_FILE" "$SUPERVISOR_PID_FILE"
  log "Supervisor stopped."
  exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# ─── Entry point ─────────────────────────────────────────────────
log "═══════════════════════════════════════════════════"
log " NEXUS-OS Supervisor v1.0 starting..."
log "═══════════════════════════════════════════════════"

preflight
supervise
