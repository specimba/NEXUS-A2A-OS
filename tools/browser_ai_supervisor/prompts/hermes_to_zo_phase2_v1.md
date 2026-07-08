# Hermes → Zo phase 2 handoff (paste into specimba Zo chat)

**From:** Hermes executor (NEXUS Windows/WSL, ModelRelay :7350)  
**To:** Zo cloud lab (`zo-computer-nexus`)  
**Grok lane:** visible Chrome CDP :9224, commit rollback `73c8e800`

## Your mission (phase 2 — CDP lane on Zo)

1. **Stand up** `services/zo_cdp_lane` (in synced NEXUS repo) as a Zo **process-mode** service:
   - `cdp_lane.ts` — Playwright `chromium.connectOverCDP(NEXUS_ZO_CDP_TUNNEL_URL)`
   - `director_policy.ts` — port of Python `external_browser_ai_director` (fingerprint, cadence, cooldown)
   - `bbon.ts` — behavior narrative JSON + judge prompt (Agent-S pattern, DOM grounding not pyautogui)

2. **Tunnel** (operator-approved): SSH `-L 9224:127.0.0.1:9224` to Windows Grok host, then:
   ```bash
   export NEXUS_ZO_CDP_TUNNEL_URL=http://127.0.0.1:9224
   bun run services/zo_cdp_lane/cdp_lane.ts probe
   ```

3. **E2E smoke:** claw task → CDP probe Grok tab → agent-browser snapshot → write `behavior_narrative` → judge picks winner → append JSONL memory (`source_id`: `zo-browser-lab`).

4. **Reply format** (required):
   - Tag `[ZO-PLAN]` with 5 concrete file paths on Zo
   - Tag `[HERMES-EXEC]` with one Windows-side verify command Hermes can run
   - Tag `[GROK-PASS]` if Grok browser should send next message (text only, no secrets)

## Context already on Windows

- Docs: `ZO_CDP_TUNNEL_WINDOWS_2026-07-02.md`, `GROK_ZO_CDP_LANE_GIT_SCOPE.md`
- Entry: `scripts/grok_zo_cdp_lane.ps1 -Action Probe|Restore|ZoHint`
- Do **not** mix commits with FABLE5 core — lane allowlist only.

## First deliverable

Implement **`cdp_lane.ts` probe** that prints Grok page title + URL from tunneled CDP, then paste output here as `[ZO-PLAN]`.