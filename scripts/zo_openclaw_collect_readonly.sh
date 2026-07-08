#!/usr/bin/env bash
set -u

# Read-only evidence collector for Zo/OpenClaw swarm debugging.
# Run on the Zo/modal Linux host. It writes a redacted evidence bundle under /tmp.

OUT="${1:-/tmp/zo-openclaw-evidence-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"

REDACT='s/(sk-or-v1-[A-Za-z0-9_-]{12,})/sk-or-v1-REDACTED/g; s/(oc-[A-Za-z0-9_-]{12,})/oc-REDACTED/g; s/([0-9]{8,}:[A-Za-z0-9_-]{20,})/TELEGRAM_BOT_TOKEN_REDACTED/g; s/("api_key"[[:space:]]*:[[:space:]]*")[^"]+/\1REDACTED/g; s/(OPENROUTER_API_KEY=).+/\1REDACTED/g; s/(OPENAI_API_KEY=).+/\1REDACTED/g'

write_cmd() {
  local name="$1"
  shift
  {
    echo "# command: $*"
    "$@" 2>&1
    echo "# exit: $?"
  } | sed -E "$REDACT" > "$OUT/$name.txt"
}

write_shell() {
  local name="$1"
  shift
  {
    echo "# shell: $*"
    bash -lc "$*" 2>&1
    echo "# exit: $?"
  } | sed -E "$REDACT" > "$OUT/$name.txt"
}

write_shell host "date -u; hostname; uname -a; id"
write_shell processes "ps -ef | grep -Ei '[o]penclaw|[t]ailscale|[t]elegram-claw|[m]odelrelay|[n]ode|[p]ython'"
write_shell ports "ss -ltnp 2>/dev/null | grep -E '(:80|:443|:18789|:7352|:7353|:9191)' || true"

if command -v openclaw >/dev/null 2>&1; then
  write_cmd openclaw_status_deep openclaw status --deep
  write_cmd openclaw_gateway_probe openclaw gateway probe
  write_cmd openclaw_security_audit_deep openclaw security audit --deep
  write_cmd openclaw_agent_list openclaw agent list
else
  echo "openclaw not found in PATH" > "$OUT/openclaw_missing.txt"
fi

if command -v tailscale >/dev/null 2>&1; then
  write_cmd tailscale_serve_status tailscale serve status
  write_cmd tailscale_status tailscale status
else
  echo "tailscale not found in PATH" > "$OUT/tailscale_missing.txt"
fi

write_shell health_checks "for url in http://127.0.0.1:18789/health http://127.0.0.1:18789/ http://127.0.0.1:7352/v1/health https://modal.tail5788b3.ts.net/; do echo '=== '\"\$url\"; curl -sS -m 10 -i \"\$url\" | head -80 || true; done"
write_shell openclaw_file_inventory "find /root/.openclaw -maxdepth 5 -type f 2>/dev/null | sort | while read -r f; do stat -c '%a %U:%G %s %y %n' \"\$f\" 2>/dev/null; done"
write_shell openclaw_auth_modes "find /root/.openclaw/agents -path '*/auth-profiles.json' -type f 2>/dev/null | while read -r f; do stat -c '%a %U:%G %s %y %n' \"\$f\"; done"
write_shell openclaw_model_configs "for f in /root/.openclaw/openclaw.json /root/.openclaw/agents/main/agent/models.json /root/.openclaw/logs/config-health.json; do [ -f \"\$f\" ] && echo '=== '\"\$f\" && cat \"\$f\"; done"
write_shell openclaw_recent_logs "for f in /tmp/openclaw*.log /tmp/oc-*.log /dev/shm/openclaw*.log /root/.openclaw/logs/*.log /root/.openclaw/logs/*.json; do [ -f \"\$f\" ] && echo '=== '\"\$f\" && tail -n 250 \"\$f\"; done"

cat > "$OUT/README.txt" <<EOF
Zo/OpenClaw read-only evidence bundle.

Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Host: $(hostname 2>/dev/null || echo unknown)

Primary triage:
1. If tailscale_serve_status shows HTTPS 443 proxying to localhost:18789 but health_checks shows 502 for https://modal.tail5788b3.ts.net/, the OpenClaw backend is down or listening on another port.
2. If openclaw_status_deep reports provider openai without OPENAI auth, fix the active main-agent model mapping before testing the dashboard.
3. If security audit reports host-header fallback or auth-profiles mode warnings, fix those before exposing the dashboard again.
4. Do not publish this bundle without reviewing redaction.
EOF

echo "$OUT"
