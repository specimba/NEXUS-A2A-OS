#!/usr/bin/env bash
# openclaw_install.sh — pre-paired OpenClaw installer (DRAFT, do not run on live node)
#
# Purpose: bootstrap OpenClaw on a fresh node so dashboard + CLI pairing
# does not require the manual paired.json edit that was used as break-glass
# on 2026-05-26.
#
# Status: DRAFT. Not tested. Not staged. Not committed.
# Intended dry-run target: a fresh container, not the live Modal sandbox.
#
# Operator approval gates are marked with ### APPROVAL ###.

set -euo pipefail

NODE_LABEL="${NODE_LABEL:-zo-modal-1}"
OPENCLAW_HOME="${OPENCLAW_HOME:-/root/.openclaw}"
LISTEN_HOST="${LISTEN_HOST:-127.0.0.1}"
LISTEN_PORT="${LISTEN_PORT:-18789}"

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

### APPROVAL ###
# Operator must confirm: (1) target host has no existing OpenClaw install
# OR (2) existing install is being intentionally replaced and backed up.
if [[ -d "$OPENCLAW_HOME" ]]; then
  log "FATAL: $OPENCLAW_HOME already exists. Back up + remove before re-running."
  exit 1
fi

log "Step 1: install OpenClaw binary"
# npm i -g @openclaw/cli   # placeholder — actual install path TBD per release channel

log "Step 2: bootstrap config with explicit loopback bind"
mkdir -p "$OPENCLAW_HOME"
cat > "$OPENCLAW_HOME/openclaw.json" <<JSON
{
  "gateway": {
    "mode": "local",
    "listen": { "host": "$LISTEN_HOST", "port": $LISTEN_PORT },
    "controlUi": { "allowedOrigins": [] }
  }
}
JSON

log "Step 3: generate gateway token + dashboard device pre-pair"
GATEWAY_TOKEN="$(openssl rand -hex 24)"
DEVICE_TOKEN="$(openssl rand -hex 32)"
DEVICE_ID="$(uuidgen)"

# Inject gateway token (auth + remote) — values never echoed
python3 - <<PY
import json, os, sys
p = "$OPENCLAW_HOME/openclaw.json"
with open(p) as f: c = json.load(f)
c.setdefault("gateway", {})
c["gateway"]["auth"]   = {"mode": "token", "token": "$GATEWAY_TOKEN"}
c["gateway"]["remote"] = {"token": "$GATEWAY_TOKEN"}
with open(p, "w") as f: json.dump(c, f, indent=2)
os.chmod(p, 0o600)
PY

mkdir -p "$OPENCLAW_HOME/devices"
python3 - <<PY
import json, os, time
p = "$OPENCLAW_HOME/devices/paired.json"
entry = {
  "$DEVICE_ID": {
    "label": "$NODE_LABEL-bootstrap",
    "token": "$DEVICE_TOKEN",
    "scopes": ["operator.admin", "operator.pairing", "operator.read", "operator.write"],
    "approvedAt": int(time.time() * 1000),
    "approvedAtMs": int(time.time() * 1000),
    "createdBy": "installer"
  }
}
with open(p, "w") as f: json.dump(entry, f, indent=2)
os.chmod(p, 0o600)
print("device pre-paired")
PY

echo "$DEVICE_TOKEN" > "$OPENCLAW_HOME/.bootstrap-device-token"
chmod 600 "$OPENCLAW_HOME/.bootstrap-device-token"

log "Step 4: register the gateway as a managed service (Zo: user-service; Linux: systemd unit)"
# Zo path:
#   register_user_service mode=process entrypoint="openclaw gateway --verbose" workdir=$OPENCLAW_HOME
# Linux path:
#   /etc/systemd/system/openclaw-gateway.service (template not duplicated here)

log "Step 5: smoke test (no token printed)"
# curl -sS http://${LISTEN_HOST}:${LISTEN_PORT}/health
# Expect: {"ok":true,"status":"live"}

log "Step 6: hand off"
cat <<HAND
Install complete.
Gateway URL:  http://${LISTEN_HOST}:${LISTEN_PORT}
Token files:  $OPENCLAW_HOME/openclaw.json (0600)
              $OPENCLAW_HOME/devices/paired.json (0600)
              $OPENCLAW_HOME/.bootstrap-device-token (0600)

Operator next steps:
  1) Configure Tailscale Serve target: tailscale serve --bg --https=443 http://${LISTEN_HOST}:${LISTEN_PORT}
  2) Open dashboard from a paired browser; paste the bootstrap device token once.
  3) Delete the bootstrap-device-token file after first successful dashboard login.
  4) Run the redaction filter (./redaction_filter.py) before sharing any logs.
HAND
