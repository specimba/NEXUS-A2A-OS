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
Port plane: 7350 relay, 7352 brain-only, 7354 canonical 25-tool MCP, 7357 God Mode, 9224 CDP; 7358 is free optional — never invent or repurpose ports.
Local models: 8GB ceiling; 35B cloud-only; Mythos OBLITERATED; VibeThinker not tool agent.
Qwen success = Preview DOM. GLM = model lock 5.2. Intern GPU for train/merge; Modal for image studio.
Plan first ≤5h using §8 PLAN table; when plan budget hits 0, auto-continue §8 EXEC without waiting.
Append JSONL to NEXUScontinuity_runs.jsonl every milestone.
Do not re-implement working P0 MCP tools; wire and test them.
Admin-only: restart an elevated owner only for an evidenced source cutover; canonical 7354 was recycled successfully on 2026-07-12.
Claw hostile bank: deferred until operator opens.
```

---

## 11. Immediate human asks (minimal)

1. **No 7354 action pending**: it is canonical, loopback-bound, 25-tool, and proposal-only as of the 2026-07-12 live probe.
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

---

## 14. 2026-07-12 revised whole-system convergence plan

This dated revision supersedes only stale operational assertions above. It is
grounded in current port probes, focused tests, the last-eight-hour Commander,
Leanstral/OpenCode, and Grok build logs, and the append-only continuity ledger.
It does not treat a transcript claim as deployment proof.

### 14.1 Current verified state

| Surface | Verified state | Boundary that remains important |
|---------|----------------|----------------------------------|
| Port plane | `nexusctl ports doctor`: required 5/5 up; 7350, 7352, 7354, 7355, 7357, and 9224 all reachable | 7352 remains Brain-only; 7358 is free optional, never a shadow production MCP port |
| ModelRelay | 236 `/api/models` rows and 134 projected `/v1/models` rows | Catalogue visibility is not provider health or a benchmark result |
| Frontier models | NVIDIA GLM-5.2 is visible at 1M context; MiniMax-M3 is visible; Leanstral is visible with `intell: null` and `isEstimatedScore: true` | Unknown benchmark evidence must stay null, never become a synthetic 45% or 50% |
| God Mode | 7357 now distinguishes scored candidates from catalogue fallback and exposes measured intelligence as measured | `pending` means routable catalogue metadata, not verified upstream availability |
| MCP / A2A | 7354 has 25 tools, loopback binding, and proposal-only inbound A2A | An external caller cannot self-approve; execution needs a governed re-dispatch |
| Browser A2A | A response requires assistant-side CDP tail growth plus durable event offsets; Qwen additionally requires Preview DOM proof | A token visible in the user prompt is never a success signal |
| Hermes | Ubuntu Hermes has an atomically written ModelRelay block, authenticated WSL gateway access, and 134 projected models | Windows Hermes was deliberately left unchanged because its endpoint is anonymous, not authenticated |
| Grounding | All roots are readable and the store is writable, but doctor remains `degraded` for one historical malformed event | Preserve the honest degraded status; repair via append-only evidence, not silent deletion |

### 14.2 The target control plane

```text
Provider catalogues / benchmark sources
  -> Frontier scanner (read-only snapshots, provenance, no auto-promotion)
  -> Model card contract (identity, health, score evidence, freshness, cost, tool support)
  -> ModelRelay 7350 -> God Mode 7357 -> Brain 7352 / GMR
                                      -> Hermes, OpenCode, Kilo, MCP clients

Browser / A2A lanes
  -> CDP 9224 evidence capture
  -> Agent Card / A2A ingress 7354
  -> TrustKernel -> KAIJU -> NexusClawTaskEnvelope
  -> explicit privilege policy -> approved executor only
  -> hashed evidence -> Vault / continuity ledger

Local 8GB lane
  -> T0 anchors -> T1 guards -> one rotatable T2 specialist
  -> cloud or browser elevation only when evidence, trust, and budget permit
```

The principal rule is separation of concerns: `catalogue discovery`, `live
provider health`, `benchmark quality`, `route eligibility`, and `operator
approval` are five distinct signals. No single score or status may stand in
for another.

### 14.3 Model stack contract

| Tier | Purpose | Allowed shape | Promotion gate |
|------|---------|---------------|----------------|
| T0 | intent, tool-shape, embeddings | FunctionGemma/BashGemma/embedding anchor class | fixed local budget and deterministic tests |
| T1 | prompt/tool governance | Guard cascade and deterministic L0 preprocessors | recall/FPR, decision-token validation, no raw secret retention |
| T2 | local specialist | one 3B-class rotatable task/tool model under the 8GB ceiling | task-specific benchmark and VRAM measurement |
| T3 | cloud frontier | GLM-5.2, MiniMax-M3, DeepSeek V4, Nemotron, LongCat, InternAI through provider-scoped policy | identity match, live health evidence, quota/cooldown, score provenance |
| T4 | collaborative escalation | CDP Trinity/Fugu or approved A2A panel | governed envelope, independent evidence, durable handoff |

35B-class weights remain cloud/A2A-only. Modal remains image-only. Intern
compute is an explicitly leased `/data` GPU lane, not an unattended browser
automation target.

### 14.4 Convergence waves and ordered backlog

#### Wave 0 - truth and safety foundation (completed or verified)

1. Canonical continuity append locks and liveness/doctor honesty.
2. Node Relay NVIDIA pacing/cooldown and no startup chat fanout.
3. GLM-5.2 and Leanstral catalogue visibility, safe unknown score markers,
   and Hermes WSL provider projection.
4. Canonical 7354 25-tool MCP cutover with proposal-only A2A. The smoke task
   `a2a-smoke-20260712013332` remained `proposed` / `dry_run` even when the
   external client requested `live` and claimed approval.
5. Browser A2A success gate: assistant evidence plus Qwen Preview proof.

#### P0 - next bounded execution slices

| Order | Deliverable | Exact integration seam | Acceptance gate |
|------:|-------------|------------------------|-----------------|
| P0.1 | Finish one model-card score contract | `nexus_os/relay/bridge_client.py`, `nexus_os/relay/god_mode_proxy.py`, Node Relay payload | Unknown dimensions remain null with provenance; no 0.45/0.50 synthesis; tests cover known, unknown, and fallback cases |
| P0.2 | Consume the existing arena sidecar rather than another hand-maintained score table | `nexus_os/relay/arena_ingest.py` -> `~/.nexus/arena/scores.json` -> bridge/God Mode read path | Each route explanation reports source, fetched time, confidence, and coverage; stale/no-data cannot raise a model |
| P0.3 | Provider freshness and opportunity intake | `tools/frontier_scanner/` plus quarantined OmniRoute catalogue adapter | Snapshots are hashed, bounded, read-only; new/free offers become candidates, never automatic routes or secret-bearing config |
| P0.4 | NIM reliability proof | Node Relay retry/cooldown telemetry and provider/model-scoped 429 fixtures | Retry-After is honored; one exhausted model does not globally ban NVIDIA; tool calls are bounded and cancelable |
| P0.5 | Re-ground the historic DPO-judge claim before mutation | locate the canonical batch generator, then change only a live reference if it exists | exact source path, dry-run artifact, and license/policy check; do not replace InternAI fallback policy by string search |
| P0.6 | Grounding-record repair plan | grounding store report and append-only repair evidence | malformed historical row is quarantined/referenced; doctor becomes healthy only when the evidence chain validates |

**External catalogue note (2026-07-12):** [OmniRoute's upstream repository](https://github.com/diegosouzapw/OmniRoute) self-reports a large, changing provider/free-tier surface. Its count conflicts with earlier social claims, so NEXUS may consume only a pinned, hashed, read-only snapshot; it must not auto-install OmniRoute, import secrets, or promote offers into routes.

#### P1 - A2A / ACP integration, not replacement

1. Extend the existing A2A bus and Agent Cards with a signed identity profile,
   capability lease, expiry, and replay-resistant task id. Do not build a
   parallel bus.
2. Route all incoming A2A and ACP work through the same sequence: Bridge
   ingress -> TrustKernel -> KAIJU -> `NexusClawTaskEnvelope` -> operator
   policy -> executor -> VAP/evidence.
3. Add a durable outbox/inbox state machine: `proposed`, `approved`,
   `executing`, `verified`, `failed`, `expired`. A task can never jump from
   externally supplied `approved` to execution.
4. Keep browser controls proposal-bound. A live browser send is a separately
   authorized operation and its success is an artifact/evidence assertion,
   not DOM text presence alone.

#### P2 - measurable model and browser operations

1. Establish the benchmark matrix below and a model-card importer with source
   date, normalization method, score coverage, and freshness horizon.
2. Add a provider health ledger distinct from the benchmark ledger: latency,
   429, auth, tool-call completion, and cancellation outcomes by model and
   provider.
3. Harden CDP lane registry ownership: one canonical target per lane,
   restore/visibility verification, no duplicate-tab recovery by default.
4. Formalize the 8GB serving decision as a tested llama-server wrapper plan;
   do not re-install or re-architect an operating local stack speculatively.

#### P3 - controlled science / local evolution

1. Enforce A800-HR-001 as launcher preflight: project quota, one-kernel lease,
   no notebook creation without a bounded run id, and `/data/NEXUS` artifact
   paths.
2. Run only small, reversible guard/tool-model experiments first. Record data
   lineage, license, hardware, seed, benchmark delta, and rollback artifact.
3. Fugu/Trinity distillation may consume only verified, policy-cleared traces;
   it must not promote browser prose or unverified model scores into training
   data.

#### P4 - long-run optimization

1. Calibrated routing learns from cost, completion quality, provider health,
   and benchmark evidence with drift alarms and rollback.
2. Add release gates for model cards, provider endpoints, A2A capabilities,
   and benchmark schema changes.
3. Publish sanitized, evidence-backed model availability reports only after
   secret scanning and provenance review.

### 14.5 Benchmark matrix v1

| Family | Representative measure | Route use | Hard rule |
|--------|------------------------|-----------|-----------|
| Repo repair / SWE | curated NEXUS repair tasks plus pinned [SWE-bench](https://github.com/swe-bench/SWE-bench) Verified snapshots | code-specialist rank | retain task id, patch/test evidence, harness version, and contamination policy; audit any claimed SWE-Pro source before use |
| Fresh code | pinned [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench) release/date window, pass@1 and pass@5 | code freshness evidence | record release version and time window; do not compare scores across release windows without labeling them |
| Terminal agent | pinned [Terminal-Bench](https://github.com/laude-institute/terminal-bench) harness task and test script | end-to-end agent rank | record agent harness, container digest, model, tokens, wall time, and test result together |
| Tool use | multi-turn schema-valid tool calls and recovery | agent/tool eligibility | no credit for a call that only parses; verify effect or dry-run artifact |
| Reasoning / math | held-out math and structured planning tasks | reasoning rank | separate from code and latency scores |
| Long context | retrieval and needle-style tasks at claimed context bands | context eligibility | report actual tokens, truncation, and provider limit |
| Frontier knowledge | pinned [Humanity's Last Exam](https://github.com/supaihq/hle) or other licensed, time-stamped public evaluation source | model-card enrichment | record source/version/date; do not blend incomparable leaderboards blindly |
| Guard | ASR, recall, FPR, decision-token integrity, and tool-injection resistance | safety gate | run white-box checks where required; prompt format is part of the result |
| Browser/A2A | assistant tail change, artifact proof, handoff integrity | lane reliability | Qwen needs Preview DOM; token echoes are unproven |
| Provider resilience | p50/p95 latency, 429, timeout, auth, cancellation | route health | provider/model scoped; no global ban from one offer failure |

Every score row must include: canonical model identity, provider identity,
metric family, raw value, normalized value, source URL or artifact hash,
fetched timestamp, freshness horizon, coverage, and confidence. Absent data is
`null` / `no_data`, not a default score.

### 14.6 Next execution order

1. Wire arena sidecar evidence into bridge/God Mode read paths with focused
   tests and a no-network fixture.
2. Add NIM retry/429 contract fixtures and expose cooldown reason without
   degrading unrelated provider models.
3. Locate and verify the real DPO generator before changing the historical
   judge string.
4. Add model-card freshness provenance to the 7356/7357 UI surfaces.
5. Only then start an explicitly leased Intern smoke or local-model serving
   wrapper change.

All milestones continue to append to `NEXUScontinuity_runs.jsonl`; live status
must be re-probed before any future claim of completion.
