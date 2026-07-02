# NEXUS CDP x Zo x Agent-S patterns — mutation architecture (2026-07-02)

Post-login CDP verified on Windows. Merge map for Hermes + Grok lane + Zo computer.

Do not install simular-ai/Agent-S wholesale (pyautogui + UI-TARS GPU). Import control patterns only.

## CDP check after login

- Tab: NEXUS OS (clone) - Grok; project 99253cca; chat 4d8d8598
- Probe: READY; Ask Grok anything
- Thread: Thought markers, 30 sources — live partner thread
- Fingerprint changed after login (material delta); director RETRY_LATER = provider_cooldown, not auth
- Profile: %LOCALAPPDATA%\\NEXUS\\BrowserAI\\ChromeProfile; CDP 9224
- Passkey: visible Chrome only (scratch/show_grok_lane_for_passkey.ps1)

Director (any cwd):

    powershell -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_supervisor\run_external_director.ps1 -RequiresBridge

run_external_director.ps1 now uses $PSScriptRoot repo root and .venv python.

## Three stacks

**A. NEXUS CDP (Windows, in repo):** Node CDP mjs + external_browser_ai_director.py + 7354 MCP. Runbook GROK_CDP_DIRECTOR_RUNBOOK_2026-06-21.md.

**B. Zo (Linux):** agent-browser + Playwright connectOverCDP to 9224 when tunneled. DOM grounding, not pixels.

**C. Agent-S (patterns):** bBoN judge rollouts; procedural memory to skills/prompts; reflection via fingerprint deltas. Reject pyautogui for Grok lane.

## Mutation diagram

Windows: Chrome BrowserAI :9224 -> Node probe/paste -> Python director -> Hermes 7350.
Zo: Playwright/agent-browser -> same CDP via tunnel -> parallel claws + judge -> handoff to Hermes.

OpenClaw/bridge: same memory schema nexus.browser_ai.supervisor.memory.v1.

## Phases

Phase 1: passkey path; director cwd fix; nexus-bbon skill stub; optional delegate_task judge.
Phase 2: Zo agent-browser connect docs for 9224 tunnel.
Phase 3: Grok paste grounding prompts; ARCHIVIST narratives.

## Security

Do not automate one-time secret URLs. Rotate exposed credentials.

## Commands

show_grok_lane_for_passkey.ps1 | run_external_director.ps1 -RequiresBridge | grok_cdp_paste_submit.mjs | nexusctl grok-lane doctor