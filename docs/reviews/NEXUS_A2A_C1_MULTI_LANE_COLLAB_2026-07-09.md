# NEXUS A2A Cycle-1 Multi-Lane Collab — Live Session Notes

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **CDP** | Chrome :9224 authenticated profile |
| **Ledger** | `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl` |
| **Orchestrator tools** | `lane_stack_preflight.mjs`, `multi_lane_a2a_cycle.mjs`, `grok_cdp_director.mjs` |
| **Prompts** | `tools/browser_ai_supervisor/prompts/a2a_cycle1/` |

## Log vs chat wording (not two strategies)

Earlier, the **chat reply** and **vault SECTION Y** described the same 6-layer stack with different prose density:

| Layer | Same intent in both |
|-------|---------------------|
| 1 | Preflight → STACK_READY |
| 2 | Send via `send_*_cdp` / director |
| 3 | Wait growth-aware |
| 4 | Probe / page text search |
| 5 | Ledger receipt |
| 6 | Optional full supervisor + VISIBLE_LANES |

Differences were **style** (bullets vs numbered steps, extra Hermes notes), not conflicting runbooks. Going forward vault text and chat should stay aligned on the same numbered protocol.

## Phase 0 — Operator-confirmed

- `lane_stack_preflight.mjs --observe` → **STACK_READY** all 7 core lanes
- Grok browser proof earlier: **`NEXUS_PROOF_OK`** received on Grok 4.3 lane
- `fix_lane` without `-ManualObservation` correctly blocked (manual-only)

## Phase 1 — Full multi_lane_a2a_cycle (~22 min)

| Lane | Status | Notes |
|------|--------|-------|
| grok | SEND_UNCERTAIN (later fixed) | Long prompts + land detection weak |
| chatgpt | SEND_FAILED then fixed | Sleeping tab → NO_VISIBLE_INPUT |
| deepseek | SEND_FAILED / land false | Prefill ok; submit still flaky |
| gemini | land true once; search empty later | Discarded DOM after sleep |
| qwen×2 | SEND_FAILED | Same wake/composer issues |
| glm52 | SEND_UNCERTAIN | 3 retries, stay on 5.2 rule kept |
| zo | SEND_FAILED | Boot screen `NO_VISIBLE_INPUT` |
| apodex | SEND_FAILED | Director exit 1 |

Report JSON: `NEXUSlogs/private_team_20260709_grok45_scratch/NEXUS_A2A_C1_phase1_*.json`

## Phase 1b — Hardened composer + short prompts (quality retry)

Director improvements:

- Prefer chat composers (`role=textbox`, aria Ask/Chat)
- `document.execCommand('insertText')` fill
- Explicit **Submit** click by aria-label
- Land check on first prompt line token

### Grok — SUCCESS (full collaborative protocol in-tab)

Token **`NEXUS_A2A_C1_GROK`** present. Model reply (compressed):

1. Preflight: Hermes poll CDP :9224 lane health/roles  
2. Role-send: tagged tasks to lanes  
3. Wait: timed hold with evidence tags  
4. Evidence: aggregate lane outputs  
5. Ledger: timestamp/hash central log  
6. Synth: Grok cross-lane analysis  
7. Verify: Zo cross-check / anomaly pre-emption  
8. Handoff: compile + archive for Hermes next cycle  

**Joint deliverable:** Multi-Lane A2A Capability Map  
**Owners:** Grok lead + ChatGPT / Gemini / Qwen / DeepSeek / GLM / Zo  

**HANDOFF from Grok:**

- Gemini: MCP-HF routing/telemetry specialties  
- Qwen: FunctionGemma router + dev patterns  
- GLM: full-stack prototyping strengths  
- Zo: high-capacity verification / stress tests  

### ChatGPT — MESSAGE LANDED

- After wake (restore + wait), send `landed: true`, token **`NEXUS_A2A_C1_CHATGPT`** in DOM  
- At +35s search, user message visible; model reply may still be generating on High reasoning  
- Need longer wait_lane_response for GPT High mode (often multi-minute)

### DeepSeek — PREFILL OK, SUBMIT FLAKY

- Composer filled (`Message DeepSeek` textarea)  
- `landed: false` after Enter — needs lane-specific Send control map  

### Gemini / Zo / Qwen / GLM / Apodex

- Still need longer wake + per-UI send maps; not dropped — next cycle work

## How Hermes + this agent proceed (canonical)

```
1. Preflight   lane_stack_preflight.mjs [--observe]
2. Role-send   grok_cdp_director / send_*_cdp with short tagged prompts
3. Wait        wait_lane_response (longer for High/Expert)
4. Evidence    page_text_search_cdp + context_probe
5. Ledger      NEXUScontinuity_runs.jsonl only
6. Synth       Grok (or supervisor) merges HANDOFF cards
7. Next cycle  specialty prompts (canvas, next.js, deep search, hunter)
```

## Lane advantage matrix (target, from operator intent + Grok)

| Lane | Advantage |
|------|-----------|
| Grok 4.3 | MCP + team sandbox + NEXUS implementation coordinator |
| ChatGPT 5.x | Custom MCP tools, sandbox workarounds, architecture |
| Gemini | Canvas + project folder + Google cloud packaging |
| Qwen deep | Advanced analysis / high-value research reports |
| Qwen webdev | HTML/JSON canvas build-test |
| DeepSeek | Coding collab + scout with Zo free flash paths |
| Zo | Full cloud Linux, OpenClaw/NexusClaw, Hermes hunter host |
| GLM-5.2 | Sandbox Next.js apps — **never switch model; retry** |
| Apodex | 8–15 agent deep search team reports |

## Next (continue without rush)

1. ChatGPT: wait 3–8 min High, re-search for HANDOFF body  
2. DeepSeek: map Send button / click after fill  
3. Short prompts to Qwen×2, GLM-5.2 (retries), Gemini after wake  
4. Zo: wait for full UI past `_boot`  
5. Apodex: open active chat if home-only  
6. Phase 2 synth prompt once ≥3 specialty replies exist  

## Operator commands (NO multi-line paste)

**Do not paste env + node on one line.** PowerShell will glue them and fail.

### Preferred (single command)

```powershell
.\scripts\watch_lane_stack.ps1
```

That script sets `VISIBLE_LANES`, ledger path, and runs preflight `--observe` for you.

### Manual (press Enter after EACH line)

```text
$env:VISIBLE_LANES = "1"
```

```text
$env:NEXUS_CONTINUITY_LEDGER = "C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl"
```

```text
node .\tools\browser_ai_supervisor\lane_stack_preflight.mjs --port 9224 --observe
```

### Observation note

If Chrome CDP window stays visible (not minimized off-screen), **you do not need terminal output to watch progression** — the browser tabs are the live UI. Terminal JSON is for agents/ledger only.

### Stress / paranoid lane (not Zo hide-test)

| Role | Lane | Notes |
|------|------|-------|
| Hide / long stress / paranoid sandbox | **MiMo Claw** (`mimo_claw`) | Registry: 4h daily trial sandbox, left-menu bootstrap — use this for stress/paranoid runs |
| Fast expert code / review | **DeepSeek** | Primary fast code+review lane |
| Cloud Linux hunter | **Zo** | Execution host, not default hide stress |

### DeepSeek submit map (known)

- Composer: `textarea[placeholder="Message DeepSeek"]`
- Send: `div.ds-button.ds-button--primary.ds-button--filled.ds-button--circle`
- Evidence issue: `document.body.innerText` often stays shell-only after send — need richer extract or operator visual confirm


## Continuation (same session, post Phase 1b)

### DeepSeek submit map
- Icon-only send control: `div.ds-button.ds-button--primary.ds-button--filled.ds-button--circle`
- `lane_submit_flush_cdp.mjs` clicks it; composerLen 303 → 0
- **Issue:** `document.body.innerText` stays ~92 chars shell only after submit — chat transcript may be virtualized/shadowed; evidence via body search is unreliable on this lane until frame/shadow extractor is added
- Wired primary-circle scoring into director submit click

### ChatGPT
- Composer still held draft; flush clicked **aria-label=Send prompt** (`composer-submit-btn`)
- User message in thread; UI showed "Thought for a few seconds" then Pro upsell — reply body not fully collected (High/Pro friction)
- Token present from user message; model specialty reply incomplete

### Qwen deep
- After restore still `NO_VISIBLE_INPUT` when interactive — needs longer wake/reload like Gemini

### Tools added this continuation
- `lane_submit_flush_cdp.mjs` — flush unsent drafts (DeepSeek/ChatGPT class maps)
- short prompts: `short_qwen_deep.md`, `short_qwen_webdev.md`, `short_glm52.md`

### Working proof stack (solid)
1. Preflight STACK_READY + --observe
2. Grok send/receive with tokens (`NEXUS_PROOF_OK`, `NEXUS_A2A_C1_GROK` full protocol)
3. Ledger `NEXUScontinuity_runs.jsonl`
4. Per-lane submit maps evolving (Grok Submit, ChatGPT Send prompt, DeepSeek primary circle)

Updated: 2026-07-09T17:14:50.126314+00:00


## Phase 1c — Specialty + Synth (live)

### Gemini — MESSAGE + SPECIALTY REPLY SIGNALS
- Composer: "Enter a prompt for Gemini" + Canvas editor present
- Send control: aria **Send message**
- Tokens: `NEXUS_A2A_C1_GEMINI`, Canvas, HANDOFF present
- Reply body grew (~46k chars) including handoffs to Grok (MCP suite) and Qwen-webdev (dashboard telemetry)

### Qwen webdev — MESSAGE LANDED
- Send classes: `message-input-right-button-send`, `chat-prompt-send-button`
- User turn `NEXUS_A2A_C1_QWEN_WEBDEV` in thread; model still generating / partial at last poll

### Grok SYNTH — REPLY COLLECTED ✓
Token **`NEXUS_A2A_C1_SYNTH`** with:

**Unified protocol elements** (from live tab tail):
- Lane advantage matrix (Grok, ChatGPT, Gemini, Qwen_Deep, Qwen_Webdev, DeepSeek, GLM-5.2, Zo, Apodex)
- Next 60–90 minutes timed plan (preflight → role-send → wait/ledger → Zo verify → synth → Hermes handoff)
- Cycle-2 HANDOFF list (Gemini MCP-HF experiment, Qwen FunctionGemma router, GLM prototype, Zo stress-verify)

### Submit control map (accumulated)

| Lane | Submit control |
|------|----------------|
| Grok | aria Submit |
| ChatGPT | aria Send prompt / composer-submit-btn |
| DeepSeek | ds-button--primary circle (body shell evidence issue) |
| Gemini | aria Send message |
| Qwen Studio | message-input-right-button-send |

### Session status
- **Solid multi-lane orchestration path proven** on Grok (protocol + synth) and Gemini (specialty)
- Partial: ChatGPT (upsell friction), Qwen (generating), DeepSeek (DOM shell), Zo/Apodex/GLM still open
- Not abandoned — infrastructure + maps improved for next hour of cycles

Updated: 2026-07-09T17:18:36.309302+00:00
