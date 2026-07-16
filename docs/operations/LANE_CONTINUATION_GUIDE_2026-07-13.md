# Lane Continuation Guide — 2026-07-13

> Grok Build automation continuation after 30h session.
> Status: All core infrastructure complete. Remaining = lane-by-lane mapping + A2A Cycle 2.

## Current Browser State (verified 2026-07-13)

| # | Lane | Tab Title | URL | Status | Input | Submit |
|---|------|-----------|-----|--------|-------|--------|
| 1 | Grok | NEXUS OS (clone) - Grok | grok.com/project/99253cca... | ✅ READY | textarea role=textbox | aria Submit |
| 2 | ChatGPT | Nexus Browser Collab Plan | chatgpt.com/c/6a4600ec... | ✅ READY |Composer textbox | aria Send prompt |
| 3 | Gemini | AI Expert Orchestrates R&D... | gemini.google.com/app/6fba62a5... | ✅ READY | textarea | hasSubmit=false (canvas-based) |
| 4 | Qwen webdev | Qwen Studio | chat.qwen.ai/c/4d6ea806... | ✅ READY | textarea | .message-input-right-button-send |
| 5 | Qdeep deep | Qwen Studio | chat.qwen.ai/c/a321e504... | ⚠️ NO_VISIBLE_INPUT | textarea (after restore) | needs longer wake |
| 6 | Z.ai (GLM-5.2) | Z.ai Advanced AI Chatbot | chat.z.ai/c/818afb28... | ✅ READY | .cm-editor contenteditable | aria Send Message |
| 7 | DeepSeek | DeepSeek | chat.deepseek.com/a/chat/s/07b0a633... | ⚠️ SHADOW_DOM | textarea | ds-button--primary circle |
| 8 | Meta AI | Meta AI | www.meta.ai/prompt/69478f17... | ⚠️ THIN_SURFACE | unknown | unknown |
| 9 | Zo Computer | NEXUS OS zo computer | specimba.zo.computer | ⚠️ UNMAPPED | unknown | unknown |
| 10 | MiMo Claw | Xiaomi MiMo Studio | aistudio.xiaomimimo.com | ✅ BOOTED | textarea | aria Send |
| 11 | MiMo (second) | Xiaomi MiMo Studio | aistudio.xiaomimimo.com | ✅ BOOTED | textarea | aria Send |
| 12 | GMI Cloud | GMI Cloud | console.gmicloud.ai | ✅ READY | textarea | unknown |
| 13 | Intern Scientist | NEXUS_scientist_v0.1 | discovery.intern-ai.org.cn | 🔴 HARD_STOP | N/A | N/A |
| 14 | GitHub (training) | specimba/NEXUS_discovery_GPU | github.com/specimba/NEXUS_discovery_GPU | READ_ONLY | N/A | N/A |

## Mapped Lanes (DOM maps exist)

| Lane | Map File | Selectors |
|------|----------|-----------|
| Qwen webdev | `docs/operations/LANE_DOM_MAPS_QWEN_DEEPSEEK.md` | `.message-input-right-button-send`, `.chat-prompt-send-button` |
| DeepSeek | `docs/operations/LANE_DOM_MAPS_QWEN_DEEPSEEK.md` | `ds-button--primary ds-button--filled ds-button--circle` |
| GLM-5.2 | `docs/operations/LANE_DOM_MAP_GLM52_CONTROL_PLANE.md` | `[aria-label='Send Message'] button`, `.cm-editor` |

## Unmapped / Problem Lanes

### DeepSeek Shadow-DOM Problem
- **Symptom**: After clicking send button, `body.innerText` stays ~92-char shell only
- **Cause**: Chat content in shadow-DOM or virtualized elements
- **Workaround**: Use `page_text_search_cdp.mjs` or visual confirmation
- **Fix needed**: Extract iframe/shadow-DOM content via CDP Runtime.evaluate

### Zo Computer Problem
- **Symptom**: Boot UI not mapped
- **Lane**: specimba.zo.computer
- **Fix needed**: Navigate to Zo tab, use context probe to discover input/submit

### Qwen Deep Tab Problem
- **Symptom**: `NO_VISIBLE_INPUT` after restore
- **Cause**: Sleeping tab needs longer wake time
- **Fix needed**: Increase wake+reload wait to 8-12 seconds

### Meta AI Problem
- **Symptom**: Thin surface, no submit button found
- **Fix needed**: Navigate to Meta AI, discover input elements

### Apodex Missing
- **Symptom**: No Apodex tab open
- **Fix needed**: Open new tab or navigate existing browser to apodex.ai

## PowerShell Recipes for Operator

### Recipe A: Probe All Lanes
```powershell
cd C:\Users\speci.000\Documents\NEXUS
node tools\browser_ai_supervisor\lane_stack_preflight.mjs --port 9224
```

### Recipe B: Probe Specific Lane
```powershell
cd C:\Users\speci.000\Documents\NEXUS
node tools\browser_ai_supervisor\grok_cdp_context_probe.mjs --port 9224 --required chat.qwen.ai --pickFirst
```

### Recipe C: Deduplicate Lane Tabs
```powershell
cd C:\Users\speci.000\Documents\NEXUS
node tools\browser_ai_supervisor\dedupe_lane_tabs_cdp.mjs --port 9224 --match 'chat\.deepseek\.com'
```

### Recipe D: Restore Lane Window
```powershell
cd C:\Users\speci.000\Documents\NEXUS
node tools\browser_ai_supervisor\grok_cdp_restore_window.mjs --port 9224 --mode normal --match 'deepseek\.com'
```

### Recipe E: Send Message to Grok (with dedupe + restore + verify)
```powershell
cd C:\Users\speci.000\Documents\NEXUS
$env:VISIBLE_LANES='1'
$env:NEXUS_CONTINUITY_LEDGER='C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl'
.\tools\browser_ai_supervisor\send_grok_cdp.ps1 -PromptFile 'tools\browser_ai_supervisor\prompts\grok\PROMPT_FILE.md' -WaitForResponse
```

### Recipe F: Search Page Content
```powershell
cd C:\Users\speci.000\Documents\NEXUS
node tools\browser_ai_supervisor\page_text_search_cdp.mjs --port 9224 --required deepseek.com --query 'NEXUS_A2A_C1_DEEPSEEK'
```

### Recipe G: Full Living Organism Check
```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\.venv\Scripts\python.exe -m nexusctl ports doctor --band-only
.\.venv\Scripts\python.exe -m nexusctl grok-lane doctor
.\tools\browser_ai_supervisor\control_surface_doctor.ps1 -Json -RequiredUrlPattern 'grok\.com'
```

## A2A Cycle 2 Plan

### Target Lanes (7 lanes)
1. **Grok** — coordinator + synthesizer (primary)
2. **ChatGPT** — MCP architecture review
3. **Gemini** — cloud deployment recommendations
4. **Qwen deep** — deep research + scoring
5. **DeepSeek** — fast code review
6. **Z.ai (GLM-5.2)** — build-test Next.js sandbox
7. **Meta AI** — lightweight HTML/CSS tricks

### Protocol (8 steps per token)
1. Preflight Hermes poll CDP 9224
2. Role-send tagged tasks with evidence expectations
3. Wait for evidence tokens in each lane's DOM
4. Aggregate evidence into ledger
5. Synthesize via Grok
6. If Zo is mapped, verify via Zo
7. Hermes handoff archive
8. Ledger update + snapshot

### Evidence Tokens (use these exact strings)
| Lane | Token |
|------|-------|
| Grok | NEXUS_A2A_C2_GROK |
| ChatGPT | NEXUS_A2A_C2_CHATGPT |
| Gemini | NEXUS_A2A_C2_GEMINI |
| Qwen | NEXUS_A2A_C2_QWEN |
| DeepSeek | NEXUS_A2A_C2_DEEPSEEK |
| GLM-5.2 | NEXUS_A2A_C2_GLMM52 |
| Meta | NEXUS_A2A_C2_META |

### Cycle 2 Research Questions
1. Which remaining P0 items (DPO judge wiring, Arena V2→GMR wiring) have implementation-ready evidence?
2. What is the optimal cherry-pick order for the 30 commits on CODEX_SOLv1?
3. Which lane's DOM can be fully mapped for reliable automation?

## Remaining Operator Actions

1. Run `lane_stack_preflight.mjs --port 9224` to verify current state
2. For each blocked lane, run context probe and document selectors
3. Open PowerShell, `cd` to repo, run recipes A-G as needed
4. After mapping, run A2A Cycle 2 with 7 lanes
5. Update NEXUScontinuity_runs.jsonl per NEXUSLOGS-GB-001
