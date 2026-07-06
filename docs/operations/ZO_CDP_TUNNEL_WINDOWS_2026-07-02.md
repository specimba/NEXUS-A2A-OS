# Zo CDP tunnel to Windows Grok lane (dedicated procedure)

Operator-approved only. Binds Grok session on Windows :9224 to Zo Playwright/agent-browser.

## Windows (Grok host)

1. Chrome **visible**, profile `BrowserAI\ChromeProfile`, CDP **9224**.
2. Do not use `-SilentBackground` for collab sessions.
3. Optional restore:

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\scripts\grok_zo_cdp_lane.ps1 -Action Restore
```

## Tunnel (pick one)

### A. SSH reverse from Windows to Zo (Zo reaches Windows CDP)

On Windows (OpenSSH server listening, firewall rule for 22):

```powershell
# Example: forward local 9224 to Zo loopback 9224 (run on Windows toward Zo)
ssh -N -R 9224:127.0.0.1:9224 zo-user@<ZO_HOST>
```

On Zo:

```bash
export NEXUS_ZO_CDP_TUNNEL_URL=http://127.0.0.1:9224
agent-browser connect "$NEXUS_ZO_CDP_TUNNEL_URL"
curl -s "$NEXUS_ZO_CDP_TUNNEL_URL/json/version"
```

### B. SSH local forward from Zo (Zo client)

On Zo:

```bash
ssh -N -L 9224:127.0.0.1:9224 windows-user@<WINDOWS_LAN_IP>
export NEXUS_ZO_CDP_TUNNEL_URL=http://127.0.0.1:9224
npx playwright codegen --browser=chromium --connect-over-cdp="$NEXUS_ZO_CDP_TUNNEL_URL"
```

## Env (NEXUS + Zo)

| Variable | Meaning |
|----------|---------|
| `NEXUS_GROK_CDP_PORT` | Windows CDP (default 9224) |
| `NEXUS_GROK_PROJECT_CHAT_URL` | Grok project chat tab |
| `NEXUS_ZO_CDP_TUNNEL_URL` | Zo-side URL to reach CDP (often `http://127.0.0.1:9224` after SSH) |
| `NEXUS_ZO_SOURCE_ID` | A2A memory id (default `zo-browser-lab`) |

## Verify handshake

Windows:

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action Probe
```

Zo:

```bash
curl -s http://127.0.0.1:9224/json/list | jq '.[] | select(.url|test("grok")) | {title,url}'
```

## A2A pass

1. Zo runs experiment, writes behavior narrative JSON to ARCHIVIST.
2. Grok (browser) gets `[GROK-PLAN]` via `grok_cdp_director.mjs --send`.
3. Hermes verifies on disk; never merges lane commits with FABLE5 core files.

See `GROK_ZO_CDP_LANE_GIT_SCOPE.md`.