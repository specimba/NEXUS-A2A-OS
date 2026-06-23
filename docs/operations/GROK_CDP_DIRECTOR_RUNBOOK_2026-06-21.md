# Grok CDP Director Runbook - 2026-06-21

## Result

Stable Grok director reach was achieved through a dedicated authenticated Chrome
profile with Chrome DevTools Protocol (CDP), not through Playwright or a fresh
in-app browser.

Valid control surface:

- Browser: dedicated Chrome profile
- CDP port: `9224`
- Profile directory: `%LOCALAPPDATA%\NEXUS\BrowserAI\ChromeProfile`
- Target: `https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba`

Invalid control surface discovered:

- CDP `9222` exists, but it is OBS/browser-source CDP only.
- It exposes `botrix`, `streamlabs`, `streamelements`, and similar pages.
- It must not be used for Grok, Zo, Z.ai, Qwen, Gemini, or AI Studio director cycles.

## Commands

Start the dedicated Grok browser profile:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_supervisor\start_browser_ai_profile.ps1 -Port 9224 -Url 'https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba'
```

Verify the target exists:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_supervisor\control_surface_doctor.ps1 -CdpPorts 9224 -RequiredUrlPattern 'grok\.com' -Json
```

Probe visible Grok state:

```powershell
node tools\browser_ai_supervisor\grok_cdp_director.mjs --port 9224 --required Grok
```

Send one bounded director prompt:

```powershell
node tools\browser_ai_supervisor\grok_cdp_director.mjs --port 9224 --required Grok --send --promptFile tools\browser_ai_supervisor\prompts\grok_director_next_artifact.md
```

If the prompt fills but does not submit, use low-level CDP submit:

```powershell
node tools\browser_ai_supervisor\grok_cdp_submit_existing.mjs --port 9224 --required Grok
```

## Verified 2026-06-21 Cycle

- `control_surface_doctor.ps1` on port `9224` returned `OK_CDP` for Grok.
- `grok_cdp_director.mjs` detected `NEXUS OS (clone) - Grok`, one textbox, and the submit controls.
- The first DOM submit filled the input but did not submit.
- `grok_cdp_submit_existing.mjs` plus the corrected submit path caused Grok to generate a response.
- Grok produced a single advisory artifact: `mcp-egress-governor/SKILL.md`.

## Grok Artifact Assessment

Artifact: `mcp-egress-governor`

Useful content:

- Correctly focuses on governed MCP/HTTP egress for sandboxed environments.
- Aligns with NEXUS governance lanes: TokenGuard, KAIJU, audit, proxy/bridge fallback.
- Proposes a bounded verification cycle and one artifact only.

Do not directly paste as production code:

- The Python stub contains syntax defects such as spaced identifiers.
- Imports are placeholders and do not match verified local module paths yet.
- Proxy backend is simulated.
- Local NEXUS integration must be rewritten by Codex and verified with tests.

Local next action:

- Convert the advisory artifact into a real NEXUS design/implementation slice only after checking existing `mcp_client`, bridge, governor, TokenGuard, and KAIJU interfaces.
- Keep it dry-run first.
- Add tests before any egress bridge is used in a live workflow.

## Automation Rule

Browser-AI automation may run only when:

1. `control_surface_doctor.ps1` confirms the required target on the requested CDP port.
2. The director probe finds a visible input or a readable completed artifact.
3. The previous run memory does not show the same blocker twice.
4. Exactly one bounded prompt or one bounded read is performed.

If any condition fails, exit with `NOTIFY_SETUP_REQUIRED` or `DONT_NOTIFY`; do
not open a blank browser, do not retry in Playwright, and do not create a new
conversation.
