# NEXUS — GPT-5.6 SOL ULTIMATE / CODEX Grounding & Master Plan

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Audience** | Codex + GPT-5.6 SOL ULTIMATE (and any long-run orchestrator) |
| **Mode** | **5h planning quota → 0 remaining → automatic execution continues** |
| **Policy** | GND-001 full-coverage; no surface-only reads of critical logs |
| **Doctrine** | FABLE5 style: plan ready-to-execute, then self-drive |

---

## 0. How to use this document (Codex bootstrap)

1. Read this file **end-to-end** before coding.
2. Open listed **Source of Truth** paths; do not invent ports, models, or lane success criteria.
3. During **first ≤5h**: produce/update plans, gap map, bench matrix, wire diagrams — **no large refactors without plan section signed**.
4. When planning budget ends (**0 quota left**): switch to **execution mode** — implement P0→P1 from §8 in order, log every step to continuity ledger.
5. Never claim stack UP without probing live ports / tests.

### Continuity ledger (append every meaningful step)

```
C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl
```

Kind examples: `plan_phase`, `exec_p0`, `bench_run`, `intern_gpu_session`, `lane_stack_preflight`, `mcp_registry`.

---

## 1. Source of Truth map (multi-root)

| Root | Path | What lives here |
|------|------|-----------------|
| **Main repo** | `C:\Users\speci.000\Documents\NEXUS` | Code, registry, ModelRelay, NexusClaw, tests, docs/plans |
| **Living logs** | `C:\Users\speci.000\Downloads\NEXUSlogs` | Agent transcripts, continuity JSONL, GO artifacts |
| **Archivist** | `C:\Users\speci.000\Downloads\ARCHIVIST` | DOM maps, papers intake, science notes |
| **Papers** | `...\ARCHIVIST\PAPERS` | Training/merge/abliteration scientific base |
| **Cold storage** | `D:\` | Models, backups, benchmarks, ollama, safetensors, NEXUS_MODELS, GROSS |

### Must-read logs (latest plan density)

| File | Lines (order) | Focus |
|------|---------------|-------|
| `NEXUSantiGRAVnexlog-11.txt` | ~12.5k | Final local SLM stack, Fugu/Trinity, training/merge, implementation plan — **read last sections + already distilled** `docs/plans/NEXUS_MODEL_USAGE_PLAN_2026-07-10.md` |
| `NEXUSkilocodeORCHESTRATORagentlogs-06.txt` | large | Grounding sweep completion, model usage plan write, collision warnings (Codex/OpenCode/Grok) |
| `NEXUSgeneralFABLE5advisorylogs-01.txt` (+02/03) | large | Registry purge, ModelRelay live, 4h sync, DPO/provider discipline — **plan→execute pattern** |
| `NEXUSbuildubuntuGROK45logs-01/02.txt` | growing | Multi-lane A2A, MCP P0 tools, GLM control plane, CDP, logging rules |
| `NEXUScontinuity_runs.jsonl` | append-only | Machine-readable session truth |

### Distilled plans already in repo (do not rewrite from scratch)

- `docs/plans/NEXUS_UPGRADED_PLAN_2026-07-08.md` — master 07-08  
- `docs/plans/NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md` — 3.5B cascade (approval-pending M1)  
- `docs/plans/NEXUS_MODEL_USAGE_PLAN_2026-07-10.md` — antiGRAV-11 distillation  
- `docs/plans/NEXUS_MILESTONES_2026-H2.md` — M0–M6  
- `docs/operations/NEXUS_MULTI_LANE_A2A_DOCTRINE.md` — lane roles  
- `docs/operations/INTERN_AI_SHANGHAI_WORKBENCH_CONTINUITY.md` — GPU lab  
- `docs/operations/GLM52_LEDGER_WIRE.md` + `LANE_DOM_MAP_*`  
- `docs/policies/GND-001_24h_deep_grounding.md`  
- `01_PROJECT_STATE.md`, `AGENTS.md` (port ownership)

### D:\ orientation (models / cold)

```
D:\NEXUS_MODELS, D:\ollama_models, D:\MyModels, D:\safetensors_candidates
D:\BACKUPS, D:\NEXUS_COLD, D:\NEXUS_RECOVERY, D:\Ollama_Backup
D:\GROSS, D:\NEXUS_OS_AUDIT, D:\cache
```

Treat D:\ as **weight/checkpoint store**; C:\Documents\NEXUS as **code**; Downloads\NEXUSlogs as **episodic memory**.

---

## 2. What NEXUS is (one paragraph)

NEXUS is a **local-first agent OS**: small specialized models + guard stack under **8GB VRAM**, elevating to **ModelRelay cloud** and **multi-lane browser A2A (CDP :9224)** for hard work; science GPU overflow on **Intern-AI Shanghai**; ops mirror on **GLM-5.2 control plane**; coordination via **MCP bridge**, **continuity ledger**, and **ChimeraRouter + ModelRelay (GMR split)**. Governance = trust kernel + monotonic privilege + Fugu/Trinity distillation — not cloud safety theater alone.

---

## 3. Live port plane (canonical — never reassign)

| Port | Owner | Status note 2026-07-10 |
|------|-------|-------------------------|
| **7350** | Node ModelRelay primary | Health historically flaky — doctor before claims |
| **7352** | Brain API / governance **only** | Never ModelRelay |
| **7354** | Grok MCP bridge SSE | **STALE elevated process 22 tools** until Admin kill; source has **25 / 2.4.0-p0-continuity** |
| **7355** | Python ModelRelay fallback | |
| **7356** | Dashboard / arena | Node |
| **7357** | God Mode proxy | |
| **7358** | **Temporary P0 MCP** | LIVE 25 tools until 7354 recycled |
| **9224** | Chrome CDP multi-lane | LIVE ~17 pages |
| **3000** | **Not** GLM CP right now | Hermes WhatsApp bridge on WSL |

---

## 4. Achievements locked (do not re-do)

### Platform / registry
- Large pytest surface historically green (4095+ pass eras); registry **v3** schema (quota, quirks, lanes).
- ChimeraRouter + ModelRelay + peer_review (Dawid-Skene) + CogER L1–L4 + tandem routing exist in tree.
- FABLE5: junk model ban, LongCat discovery, 4h `nexus_model_sync_4h.ps1`, provider credit discipline.

### Multi-lane A2A (Grok 4.5 session)
- Doctrine doc: Qwen = **Preview success**, Claw = daily stress (deferred soft cases), Zo = Ubuntu resume, GLM = model lock 5.2, Intern = primary GPU lab.
- CDP tools: preflight, keep_visible, dedupe, send maps, multi_lane_a2a_cycle.
- **P0 MCP tools in source**: `continuity_append`, `continuity_tail`, `cdp_window_probe` (25 tools).
- Live smokes: append + CDP probe OK; HTTP P0 on **:7358**.
- GLM-5.2 built **NEXUS A2A control plane** (ops board); Grammarly hydration fixed; ARCHIVIST dual-surface DOM maps.
- Qwen preview probe hardened (activate/`--reload`); honest `NO_PREVIEW_SIGNAL` when WebDev surface empty.

### Intern-AI
- Prior notebook: `NEXUS_scientist_v0.1` / job id pattern on discovery.
- Dev machine **NEXUS-GPU-test1** A100×1 stopped — restartable.
- Cloud drive 30GB `/data` + `discovery-ctl` CLI documented.

### Security / science
- MCP guard shadowing/confusion; privilege monotonic confinement; Intern Discovery SCP bridge tests.
- ARCHIVIST papers pipeline for abliteration, task arithmetic, GRPO.

---

## 5. Known blockers (honest)

| ID | Blocker | Severity | Owner |
|----|---------|----------|-------|
| B1 | :7354 elevated stale 22-tool process | P0 | **Admin terminal** |
| B2 | Cloud `_check_health` posts to Ollama for cloud models | P0 | Codex exec |
| B3 | DPO judge still `intern-s2-preview` → should `deepseek-v4-pro` | P0 | Codex exec |
| B4 | Three-lane collision on continuity substrate (Codex/OpenCode/Grok) | P0 | Human + single branch owner |
| B5 | Ollama reinstall / llama-server router (M1) | P1 | Admin + plan |
| B6 | Brain API / 7350 health regressions intermittent | P1 | doctor scripts |
| B7 | Qwen WebDev not always in Preview mode | P2 | CDP lane task |
| B8 | Claw hard CASE bank deferred (operator) | hold | later |
| B9 | ~60+ unstaged multi-lane files historically | P1 | git hygiene sprint |
| B10 | 01_PROJECT_STATE partially stale vs live GO | P2 | refresh after exec |

---

## 6. Model stack (last shape — antiGRAV-11 + FABLE5)

```
Local (8GB ceiling)
  T0 anchors: FunctionGemma-270M + BashGemma-270M + embed (~750MB)
  T1 guard: Llama-Guard-3-1B + small classifiers (~1GB)
  T2 task: Mythos-nano-OBLITERATED + refinedtoolcallv5-3B / VibeThinker family (2–2.5GB)
  T3 cloud via ModelRelay: GLM-5.2, DeepSeek-V4, Nemotron Ultra free, MiniMax-M3 (serial), LongCat, InternAI
  35B class = CLOUD A2A ONLY (never local)

Cascade: Local → Free cloud → CDP multi-LLM Fugu/Trinity when trust low / stakes high
```

**Corrections already decided:** no 35B local; Mythos **OBLITERATED**; VibeThinker ≠ tool agent; GMR = Chimera (strategy) + ModelRelay (execution).

**Heavy GPU:** Intern-AI A100 (Shanghai) for fine-tune/merge/bench — not Modal (Modal = image studio).

---

## 7. Multi-lane + pipeline interconnection map

```
                    ┌─────────────────────┐
                    │ Continuity JSONL    │
                    │ + NEXUSlogs         │
                    └──────────▲──────────┘
                               │
 ┌─────────────┐    ┌──────────┴──────────┐    ┌──────────────────┐
 │ Local SLM   │───▶│ ChimeraRouter / GMR │───▶│ ModelRelay :7350 │
 │ T0-T2 8GB   │    │ CogER L1-L4         │    │ + Python :7355   │
 └─────────────┘    └──────────┬──────────┘    └────────┬─────────┘
                               │                        │
                    trust low / complex                 │
                               ▼                        │
                    ┌──────────────────────┐            │
                    │ CDP Supervisor :9224 │◀───────────┘
                    │ Multi-lane A2A mesh  │
                    └──────────┬───────────┘
          ┌────────────┬───────┼────────┬────────────┐
          ▼            ▼       ▼        ▼            ▼
     Qwen Preview  DeepSeek  GLM CP  Gemini Drive  Zo Ubuntu
     Grok MCP      MiMo Claw  MiniMax  Mistral      Intern GPU
          │            │       │        │            │
          └────────────┴───────┴────────┴────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ MCP :7354/7358      │
                    │ continuity_* tools  │
                    │ GLM ops mirror UI   │
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Intern-AI /data     │
                    │ checkpoints+benches │
                    └─────────────────────┘
```

### Success criteria by lane (do not invent)

| Lane | Success signal |
|------|----------------|
| Qwen WebDev | Preview/Code/Deploy DOM — **not** essay length |
| GLM-5.2 | Compile + boards + STATE milestones; **model lock** |
| Grok | MCP/registry proof + synth handoffs |
| Claw | Hostile CASE bank pass (when operator opens) |
| Intern | Checkpoint on `/data`, points logged |
| Local stack | VRAM ≤8GB, guard before generator |

---

## 8. Five-hour plan phase → execution phase

### Phase PLAN (≤5h wall / planning tokens)

| Hour | Deliverable |
|------|-------------|
| H0–1 | Port doctor snapshot; git status; confirm D:\ model inventory index; refresh 01_PROJECT_STATE “live GO” bullet |
| H1–2 | Bench matrix v1 (local SLM + cloud + Intern) with pass/fail JSON schema |
| H2–3 | Wire diagram validation vs code paths (Chimera, relay, director, MCP tools) — file gap list only |
| H3–4 | Intern job pack: one A100 restart plan + dataset mount list (max 5) + `/data/NEXUS` layout |
| H4–5 | Execution backlog ordered P0→P2 with exact file paths; sign “PLAN COMPLETE → EXEC AUTO” |

**End of plan:** append `kind=plan_phase_complete` to continuity JSONL. **Do not wait for human** if operator set auto-continue.

### Phase EXEC (0 plan quota — automatic)

Order is mandatory:

1. **B1 coordination** — if Admin not done, keep using :7358; document; do not block all work.
2. **B2** fix cloud health check (`model_relay` / equivalent) + tests.
3. **B3** DPO judge string fix + regenerate batch dry-run.
4. **MCP inventory sync** — control plane `mcpTools.ts` / docs → 25 tools including P0; registry_debug match.
5. **Continuity substrate** — single owner branch; merge or fence OpenCode/Codex/Grok collisions.
6. **Stack v0 local** — only after M1 llama-server/Ollama path decided; else cloud+CDP path only.
7. **A2A integration test** — preflight STACK_READY → one handoff Grok→Qwen Preview probe → ledger row.
8. **Intern restart NEXUS-GPU-test1** — tiny smoke: torch cuda, write `/data/NEXUS/logs/smoke.txt`.
9. **Benchmark pack v0** — 5 tasks: tool-call, code, refusal-boundary (guard), math, long-context smoke.
10. **Documentation** — update 01_PROJECT_STATE + gap analysis; no motivational filler.

### FABLE5 execution style

- Prefer **code + tests + config** over essays.
- Dead models **banned** from arsenal; free tiers **probed** before primary.
- 4h model-sync remains the fan-out heartbeat for CLIs.
- When blocked on secrets/Admin: write `BLOCKED.md` one-pager and continue next unblocked P0.

---

## 9. Smart benchmark plan (minimal high signal)

| Suite | Where | Models | Metric |
|-------|-------|--------|--------|
| **Guard L1–L3** | Local | Llama-Guard + small | ASR / false block rate |
| **Tool-call multi-turn** | Local 3B tool model | refinedtoolcallv5 | success@k, schema valid |
| **Code** | Local VibeThinker / cloud DeepSeek | pass@1 on curated NEXUS tasks |
| **Fugu consistency** | CDP Trinity | 3 models | Dawid-Skene agreement |
| **Relay health** | :7350/:7355 | all TIER_PRIMARY | p50 latency, 429 rate |
| **Intern train smoke** | A100 | 1-step train + TensorBoard | loss finite, ckpt on `/data` |
| **Lane DOM** | CDP | Qwen/GLM maps | selector hit rate |

Store under `D:\NEXUS_MODELS\benches\` or `/data/NEXUS/benches/` + pointer in continuity.

---

## 10. Codex / GPT-5.6 SOL ULTIMATE system prompt fragment

Copy into Codex custom instructions or first message:

```
You are executing NEXUS under GND-001 and FABLE5.
Root of truth: docs/plans/NEXUS_CODEX_GPT56_SOL_ULTIMATE_GROUNDING_AND_MASTER_PLAN_2026-07-10.md
Repo: C:\Users\speci.000\Documents\NEXUS
Logs: C:\Users\speci.000\Downloads\NEXUSlogs
Archivist: C:\Users\speci.000\Downloads\ARCHIVIST
Weights: D:\NEXUS_MODELS and D:\ollama_models
Port plane: 7350 relay, 7352 brain-only, 7354/7358 MCP, 9224 CDP — never invent ports.
Local models: 8GB ceiling; 35B cloud-only; Mythos OBLITERATED; VibeThinker not tool agent.
Qwen success = Preview DOM. GLM = model lock 5.2. Intern GPU for train/merge; Modal for image studio.
Plan first ≤5h using §8 PLAN table; when plan budget hits 0, auto-continue §8 EXEC without waiting.
Append JSONL to NEXUScontinuity_runs.jsonl every milestone.
Do not re-implement working P0 MCP tools; wire and test them.
Admin-only: kill elevated 7354 — see ADMIN_TERMINAL_UNBLOCKS_2026-07-10.md
Claw hostile bank: deferred until operator opens.
```

---

## 11. Immediate human asks (minimal)

1. **Admin PowerShell**: run §1 of `Downloads\NEXUSlogs\ADMIN_TERMINAL_UNBLOCKS_2026-07-10.md` (kill 7354 + restart).
2. **Optional**: start Intern **NEXUS-GPU-test1** when ready for train smoke (points ~11/h).
3. **Codex**: open this plan + attach repo; enable auto-continue after plan phase.
4. **Not needed for start**: Claw cases, Modal keys, full ERA5 mount.

---

## 12. Success definition for this Codex run

- [ ] Plan phase artifacts committed or written under `docs/plans/` + continuity row  
- [ ] At least **two P0 code fixes** landed with tests (B2, B3 preferred)  
- [ ] MCP path documented/proven 25 tools (7358 or recycled 7354)  
- [ ] Bench matrix file exists with ≥5 suites  
- [ ] Intern `/data` layout + smoke instructions verified or run  
- [ ] 01_PROJECT_STATE + gap analysis updated with 2026-07-10 GO + this plan pointer  
- [ ] No false “all green” claims without probes  

---

## 13. References (pointers only)

- antiGRAV-11 final implementation plan (CDP handoff, scientific train/merge)  
- kilocode ORCHESTRATOR-06 verification of model usage plan + grounding sweep  
- FABLE5-01 registry/sync execution pattern  
- Grok45-02 GO live P0 block  
- `docs/plans/NEXUS_MODEL_USAGE_PLAN_2026-07-10.md`  
- `docs/operations/NEXUS_MULTI_LANE_A2A_DOCTRINE.md`  
- `docs/operations/INTERN_AI_SHANGHAI_WORKBENCH_CONTINUITY.md`
