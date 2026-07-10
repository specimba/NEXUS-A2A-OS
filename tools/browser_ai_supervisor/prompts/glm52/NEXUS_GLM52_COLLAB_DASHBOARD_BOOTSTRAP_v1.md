# NEXUS × GLM-5.2 — Deep Bootstrap: A2A Collab OS + MCP-aware Dashboard

**Paste everything below the line into Z.ai as GLM-5.2 only.**  
**If send fails or UI offers another model: wait 30–90s, retry GLM-5.2. Never switch.**

---

NEXUS_GLM52_BOOTSTRAP_V2

You are **GLM-5.2** on Z.ai with full sandbox + Next.js + file system. You are founding a **long-lived NEXUS control-plane app**, not a toy todo list.

## 0. Reality of the NEXUS stack (encode this in code + docs)

### Live systems (Windows host operator)
| Port | Component | Role |
|------|-----------|------|
| 9224 | Chrome CDP | Multi-lane browser truth (Grok, ChatGPT, Gemini, Qwen, DeepSeek, Zo, MiMo Claw, …) |
| 7354 | Grok MCP Bridge v2 | SSE connector tools for Grok/GPT custom connectors |
| 7352 | Brain API | Not MCP |
| 7355 | ModelRelay fallback | Internal |
| file | `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl` | Continuity ledger |

### Grok MCP tools you must model in the dashboard (22 tools, real names)
Connectivity: `ping`, `echo`, `registry_debug`  
Evidence: `audit_log`, `evidence_capture`, `http_diagnostic`, `query_log`, `comparison_add`, `comparison_get`, `comparison_export`, `simulate_probe`  
Queue: `task_add`, `task_list`, `task_claim`, `task_complete`, `task_fail`, `coordination_status`  
Session/A2A: `session_heartbeat`, `session_status`, `agent_publish_message`, `agent_retrieve_messages`, `agent_list_topics`

Hardening facts (UI must not imply shell/root):
- `http_diagnostic` is public HTTPS GET/HEAD only; private IPs blocked; no cookies/auth headers.
- No delete/shell/local FS tools on the Grok bridge.
- Runtime may fall back to `scratch/browser_ai_mcp_runtime`.

### Lane doctrine (registry.ts)
| Lane | Success signal | Wait policy |
|------|----------------|-------------|
| qwen_webdev | Preview/Code/Deploy DOM | **No chat-essay wait** |
| deepseek | Assistant markdown growth | Fast code/review |
| mimo_claw | Daily 4h red-team VERDICT | Paranoid gate |
| zo | Ubuntu + NEXUS agents | Resume summary required after pause; **not** hide-stress |
| grok | MCP + synth + Drive work folder | Coordinator |
| gemini | Canvas + Drive package | Storage bridge |
| glm52 | This sandbox | Retries only, model lock |
| intern_gpu | Shanghai A800 notebook | GPU jobs |
| minimax | general/coder/verifier | Team cycles |
| mistral_code | GitHub+Drive coder | Implementation |
| meta_muse | Fast HTML examples | Tricky collab |

## 1. Mission

Build `nexus-a2a-control-plane` (rename OK if already exists; keep STATE.md continuous):

1. **Ops mirror** of multi-lane A2A: lane cards, handoff bus, ledger tail.  
2. **MCP control panel**: show tool inventory, last ping/registry_debug payload, queue counts.  
3. **Adapters**:  
   - Ledger file reader (real path injectable).  
   - MCP client stub that can later hit `http://127.0.0.1:7354/health` and document SSE.  
   - CDP status stub (do not drive Chrome from v0 if unstable).  
4. **Resume OS**: STATE.md + scripts so a new GLM-5.2 session continues without reverse-prompt garbage.

## 2. Architecture (implement, not only describe)

```
nexus-a2a-control-plane/
  README.md
  STATE.md
  package.json
  next.config.mjs
  .env.example
  docs/
    MCP_CONTRACT.md          # tool list + allow/deny
    LANE_DOCTRINE.md
    RESUME.md
  src/
    app/
      layout.tsx
      page.tsx                 # main ops board
      mcp/page.tsx             # MCP tools + health
      lanes/page.tsx
      handoffs/page.tsx
      api/
        health/route.ts
        ledger/route.ts        # GET ?limit=30
        lanes/route.ts
        handoffs/route.ts      # GET + POST
        mcp/health/route.ts    # try fetch 7354/health; degrade gracefully
        mcp/tools/route.ts     # static inventory from MCP_CONTRACT
        mcp/queue/route.ts     # mock or file-backed queue snapshot
    components/
      LaneCard.tsx
      HandoffCard.tsx
      LedgerTail.tsx
      McpToolTable.tsx
      McpHealthBadge.tsx
      KeepVisibleBanner.tsx    # remind operator of keep_visible_daemon
      QwenWebDevNote.tsx       # "success = Preview not chat"
    lib/
      types.ts
      ledger.ts
      registry.ts
      mcpTools.ts              # TOOL_NAMES + descriptions (from deep dive)
      paths.ts
      handoffBus.ts
  data/
    sample_ledger.jsonl
    sample_handoffs.json
    sample_mcp_health.json
```

## 3. Types (minimum)

```ts
export type LaneId =
  | "grok" | "chatgpt" | "gemini" | "qwen_webdev" | "qwen_deep"
  | "deepseek" | "glm52" | "zo" | "mimo_claw" | "minimax"
  | "mistral_code" | "intern_gpu" | "meta_muse" | "apodex";

export type LaneStatus = "ready" | "partial" | "broken" | "unknown" | "preview_mode";

export type HandoffCard = {
  id: string;
  from: LaneId;
  to: LaneId;
  token: string;
  summary: string;
  artifacts: string[];
  status: "open" | "accepted" | "blocked" | "done";
  created_at: string;
  mcp_evidence_ref?: string;  // evidence_capture id/hash if any
  budget?: string;
};

export type LedgerRow = Record<string, unknown> & {
  ts?: string;
  kind?: string;
  lane?: string;
  status?: string;
  cycle?: string;
};

export type McpToolInfo = {
  name: string;
  group: "connectivity" | "evidence" | "queue" | "session" | "a2a";
  description: string;
  risk: "low" | "medium" | "high";
};
```

## 4. UI requirements (deeper than v0)

1. Dark ops aesthetic; dense but readable.  
2. Home: lane grid + last 5 handoffs + ledger tail 15.  
3. MCP page: tool table + health badge (`UP|DOWN|STUB`) + last registry hash field.  
4. Banner: “CDP :9224 is live truth. This app is the operator mirror. Run keep_visible_daemon on Windows host.”  
5. Handoff form: create card POST → appears in list.  
6. Qwen card status can be `preview_mode` with helper text.  
7. Seed data non-empty without Windows paths (use samples); document how to point `.env` at real ledger.

## 5. Env

```
NEXUS_LEDGER_PATH=C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl
NEXUS_MCP_HEALTH_URL=http://127.0.0.1:7358/health
NEXUS_MCP_SSE_URL=http://127.0.0.1:7358/sse
NEXUS_CDP_PORT=9224
```

- Prefer **7358** while elevated stale **7354** (22 tools / 2.3.0) cannot be killed without Admin.
- After Admin recycle of 7354 → `start_grok_mcp_v2.ps1` → expect **25 tools / 2.4.0-p0-continuity**; then point URLs back to 7354.
- See `docs/operations/GLM52_LEDGER_WIRE.md`.

When health fetch fails in sandbox, show STUB and still render tool inventory from `mcpTools.ts`.

## 6. Milestones (force-complete in order)

### A — Scaffold
Next.js App Router + TS + Tailwind; README; STATE.md “A done”.

### B — Domain + APIs
types, samples, all API routes including mcp/* ; STATE.md.

### C — UI boards
Home + MCP + handoffs wired; looks production-adjacent; STATE.md.

### D — MCP contract docs
`docs/MCP_CONTRACT.md` with full 22-tool table + denylist (no shell/cookies/private IP).  
`docs/RESUME.md` for next GLM-5.2 session. STATE.md “READY FOR LONG RUN”.

### E — Stretch (if context remains)
File-backed handoff store under `data/handoffs.json`; simple filter UI; optional SSE note page.

## 7. Retry protocol (high usage)

1. Fail → wait → “Continue Milestone X from STATE.md, GLM-5.2 only”.  
2. Small file batches; never one mega paste.  
3. After each batch re-read STATE.md.  
4. No model switch. No “try flash instead”.

## 8. Integration HANDOFF (when READY)

```
## HANDOFF
- Grok MCP: host app; wire real NEXUScontinuity_runs.jsonl; later add continuity_append tool
- Qwen-webdev: richer preview mirror of HandoffCard + dashboard skin
- Zo: Ubuntu job tail ledger → agent_publish_message topic nexus.a2a.handoff
- Gemini: publish playbook to shared Google Drive (Grok work folder)
- DeepSeek: review API auth surface and SSRF on mcp/health proxy
- Hermes: only one supervisor; VISIBLE_LANES=1 + keep_visible_daemon
```

## 9. Start now

Begin **Milestone A immediately**. Do not wait. Do not restate this prompt. Create files. After A, continue B→C→D without asking. Keep GLM-5.2. Update STATE.md every milestone.
