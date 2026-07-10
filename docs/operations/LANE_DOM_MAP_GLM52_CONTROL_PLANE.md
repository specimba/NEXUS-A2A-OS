# GLM-5.2 dual-surface DOM map (ARCHIVIST 2026-07-10)

Sources (last 3 ARCHIVIST dumps under `Downloads/ARCHIVIST`):

| File | What it actually mapped |
|------|-------------------------|
| `GLM52devbrowserALLpositionsREVEALED.md` | **chat.z.ai shell** — composer, Send, workspaceHeader, CodeMirror, sticky nav |
| `GLM52devbrowserALLpositionsREVEALED2.md` | Network/resources + toast UI noise (less useful for CDP send) |
| `GLM52devbrowserALLpositionsREVEALED3.md` | **Preview iframe / control-plane app** — NEXUS A2A ops board (ops mirror) |

Thread: `https://chat.z.ai/c/818afb28-dcc7-43bc-a514-1d13ebd11ec6`  
Doctrine: model lock GLM-5.2 — retries only, no flash fallback.

---

## Surface A — chat.z.ai shell (lane chat / agent)

CDP target: page URL contains `chat.z.ai`. This is where prompts land.

### Sticky / chrome

| Control | Selector / note | Approx |
|---------|-----------------|--------|
| Top model nav | `nav.sticky.top-0` (h≈52) | houses GLM-5.2 model picker |
| Workspace header | `div.workspaceHeader` | Code View / Live Preview / Publish cluster |
| Code View / Live Preview | `div.workspaceHeader … #bits-c205 > button.h-8` | **bits ids rotate** — prefer text/aria |
| Publish | `div.workspaceHeader … #bits-c210` | bits id unstable |
| Composer editor | `div.cm-editor div.cm-scroller div.cm-content` | CodeMirror contenteditable surface |
| Send Message | `[aria-label="Send Message"] button` **or** parent `div[aria-label="Send Message"] > button` | label often on **div**, not button |

### CDP control recipe (send)

1. Activate page: `url includes chat.z.ai` (conversation id optional).
2. Focus composer: `div.cm-content[contenteditable="true"]` (or first visible `.cm-content`).
3. Insert text via `Input.insertText` / Runtime.evaluate paste path (avoid relying on bits-* ids).
4. Click send: prefer  
   `document.querySelector('[aria-label="Send Message"] button')`  
   fallback:  
   `document.querySelector('[aria-label="Send Message"]')` then click nested `button`.
5. Do **not** treat chat essay length as success for WebDev tasks — if task is app-build, switch to Surface B / Preview.

### Shadow / extension noise (ignore)

- Grammarly (`data-gr-*` on body — also caused Next hydration mismatch on control plane)
- Quillbot `QB-TOOLBAR` / `#qb-toolbar-container`
- Monica / other sidebars

`bits-c###` ids are session-ephemeral — never hardcode long-term.

---

## Surface B — NEXUS A2A Control Plane (Preview / ops mirror)

What the screenshot shows: dark ops board built by GLM-5.2 inside WebDev preview (and/or localhost:3000).  
This is the **operator mirror**, not the browser driver. Live truth remains CDP `:9224` + MCP `:7354`.

### Sticky / nav

| Control | Selector / note | Approx |
|---------|-----------------|--------|
| Sticky header | `header.sticky.top-0.z-40.nexus-panel.border-b` | top 0, h≈57 |
| OPS BOARD | header nav link `/` | |
| MCP | `/mcp` | |
| LANES | `/lanes` | |
| HANDOFFS | `/handoffs` | |
| VIEW ALL → | mono cyan link | y≈375 |
| OPEN BUS → | handoffs section | y≈2109 |
| Sticky footer | `footer.mt-auto.nexus-panel.border-t` | "operator mirror — not the browser driver" |

### Lane cards (home grid)

| Lane | Status pill | Selector / notes |
|------|-------------|------------------|
| GLM-5.2 | READY | `article.nexus-panel.border-cyan-500/40`, `lane_id: glm52` |
| Qwen WebDev | PREVIEW MODE | `border-violet-500/40` — success = Preview/Code/Deploy DOM, not chat essay |

### Hydration note

Grammarly injects `data-gr-*` on `<body>`. Control plane fixed with `suppressHydrationWarning` on `<html>` and `<body>`.

### Operator use

- CDP-control this dashboard only for verification / screenshots.
- Wire real ledger via `NEXUS_LEDGER_PATH` → `Downloads/NEXUSlogs/NEXUScontinuity_runs.jsonl`.
- Handoff bus file: app-local `data/handoffs.json` until MCP continuity tools are live.

---

## Related automation assets

| Asset | Path |
|-------|------|
| P0 MCP tools | `tools/browser_ai_mcp/grok_mcp_server_v2.py` → `continuity_append`, `continuity_tail`, `cdp_window_probe` (25 tools total) |
| Qwen Preview probe | `tools/browser_ai_supervisor/qwen_preview_success_probe.mjs` |
| Qwen/DeepSeek maps | `docs/operations/LANE_DOM_MAPS_QWEN_DEEPSEEK.md` |
| GLM bootstrap prompt | `tools/browser_ai_supervisor/prompts/glm52/NEXUS_GLM52_COLLAB_DASHBOARD_BOOTSTRAP_v1.md` |

## Live retest gate (when operator says go)

1. Chrome CDP listening on `127.0.0.1:9224` (Windows host).
2. Restart Grok MCP bridge so registry shows **25** tools (not stale 22).
3. `cdp_window_probe` → sample includes `chat.z.ai` + control-plane / preview.
4. `continuity_append` smoke → row in `NEXUScontinuity_runs.jsonl`.
5. Optional: `node qwen_preview_success_probe.mjs --port 9224`.
6. **Claw hostile CASE bank: deferred** (operator: still rookie focus later).
