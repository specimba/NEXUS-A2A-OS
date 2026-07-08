# Zo CDP lane (phase 2)

Deploy on **Zo** (`specimba.zo.computer`). Connects to **Windows Grok CDP :9224** via SSH tunnel.

## Quick start (Zo)

```bash
cd services/zo_cdp_lane
bun install
export NEXUS_ZO_CDP_TUNNEL_URL=http://127.0.0.1:9224
bun run probe
```

## Modules

| File | Role |
|------|------|
| `cdp_lane.ts` | Playwright connectOverCDP probe |
| `director_policy.ts` | Fingerprint + decide (Python parity subset) |
| `bbon.ts` | Behavior narratives + judge prompt |

## A2A

- `source_id`: `zo-browser-lab` or `zo-computer-nexus`
- Chat: `NEXUS_ZO_CHAT_URL` (default specimba `con_EL8I2vKUvldsLVJ6`)

Hermes handoff prompt: `tools/browser_ai_supervisor/prompts/hermes_to_zo_phase2_v1.md`

**Composer keys (Grok + Zo):** Shift+Enter = new line; Enter = send. CDP uses `cdp_compose_submit.mjs` (multiline prompts split with Shift+Enter, final Enter submits).