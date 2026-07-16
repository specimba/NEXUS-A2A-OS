# NEXUS Deep Dive Grounding Report — 2026-07-13
## Full Coverage Synthesis: Kilo CLI · Codex SOL/TERRA · Fable5 · ARCHIVIST · NEXUSlogs

---

## 1. Executive Summary

This report synthesizes evidence from four canonical source locations:

- `C:\Users\speci.000\Downloads\NEXUSlogs` — 137+ agent transcript files
- `C:\Users\speci.000\Downloads\ARCHIVIST` — 1,590+ files (papers, dossiers, intel)
- `C:\Users\speci.000\Documents\NEXUS` — live repository (CODEX_SOLv1 branch, 129 commits ahead of main)
- `D:\` — cold storage (models, benchmarks, backups, GROSS)

The NEXUS system has deep roots — substantial subsystems built across 4+ months of intensive multi-agent work — but the trunk is not yet visible: subsystems exist but don't consume each other's outputs. Seven severed integration seams prevent the system from operating as one coherent platform.


## 2. Kilo CLI LongCat Orchestrator — Governance Brain

### Role
Kilocode is the **governance and coordination authority**, not a builder. It authored:

- **GND-001** — the 24-hour deep-grounding policy (now in AGENTS.md)
- **GAP_ANALYSIS_2026-07-09** — system-wide gap inventory
- **M0 corrections sprint** — MiniMax reclassified to restricted, DPO judge swapped to deepseek-v4-pro, length-as-covariate rule
- **Fabrication catch** — HERMES "Paranoia Engine" metrics were f.write'd, not real CDP runs; excluded from training

### Key Logs
| File | Lines | Focus |
|------|-------|-------|
| NEXUSkilocodeORCHESTRATORagentlogs-01 through 07 | 1,000-10,000+ each | Model relay ground-truth, team role map, NEXUSCLAW design, root file restoration, GuardPlane E2E tests, continuity substrate, grounding scan |
| NEXUSshangGPUcloudKILOlog-01.txt | — | Shanghai GPU cloud coordination |

### Verified Accomplishments
1. Model Relay ground-truth: port 7355 is canonical Python relay, 7352 is Brain API proxy, 7350 is Node ModelRelay
2. Team role map corrected: OpenCode/Kilo/Mimo/Cline/Hermes on NEXUS Model Relay 7355
3. NEXUSCLAW Design doc (165 lines, 12-collision analysis)
4. Root files restored: CONTRIBUTING.md, ONBOARDING.md, CLAUDE.md, NEXT_MOVEMENTS_PLAN.txt, PROJECT_GROUNDING_LEDGER.md
5. Continuity ledger repaired: 147 rows parse, lock-protected, fsync'd
6. Grounding scan: changed-only scan from 150s to 11.5s

### Open Items
- GuardPlane service source path mismatch (tests import `models/guards/guard_plane_service.py` but file absent)
- DWM GPU hog evidence captured but not remediated (RTX 4070, mismatched refresh rates 240Hz vs 74Hz, HAGS disabled)

---

## 3. Codex SOL/TERRA Progression — Planning Authority

### Role
CODEX SOL ULTIMATE (GPT-5.6) is the **integration and verification authority**. It owns task packets, branch/path leases, release claims, and schema unification.

### Key Logs
| File | Lines | Focus |
|------|-------|-------|
| NEXUSnewSOLcoordinationULTRAonCODEXlog-23.txt | 18,195 | SOL ULTIMATE boot packet, master plan, FABLE5 knowledge base, 5h plan phase then auto-exec |
| NEXUSnewSOLcoordinationULTRAonCODEXlog-24.txt | — | Continuation: OmniRoute audit, relay hardening, Hermes recovery |
| NEXUSnewSOLcoordinationULTRAonCODEXlog-25.txt | 4,973 | Last-8h grounding pass, A2A/ACP governance boundary |
| NEXUSnewTERRAcoordinationULTRAonCODEXlog-26.txt | 10,759 | Fable5 advisory, whole-system convergence plan |
| NEXUSnewTERRAcoordinationULTRAonCODEXlog-27.txt | 2,466 | TERRA continuation: model stack, relay scoring, provider landscape |

### The SOL Plan (Codex log-23)
The SOL plan defines a **5-hour planning phase then automatic execution** contract:

**Phase PLAN (section 8 table):**
- H0-1: Port doctor, git status, D: model inventory, refresh 01_PROJECT_STATE
- H1-2: Bench matrix v1 (local SLM + cloud + Intern)
- H2-3: Wire diagram validation vs code paths
- H3-4: Intern job pack (A100 restart plan, dataset mounts, /data/NEXUS layout)
- H4-5: Execution backlog P0 to P2, sign "PLAN COMPLETE then EXEC AUTO"

**Phase EXEC (automatic at 0 plan quota):**
1. B2 cloud health fix (Ollama POST bug for cloud models)
2. B3 DPO judge to deepseek-v4-pro
3. MCP 25-tool docs/UI sync
4. Continuity fence
5. A2A smoke
6. Intern smoke
7. Bench skeleton v0

### The Revised Whole-System Plan (TERRA log-26/27)
The revised plan replaces the narrow P0-only approach with **6 waves + Track A**:

**Track A — Arena Score Ingestion to Scoring v2 to CLI Wiring (5 slices)**
- A1: Arena ingestion core (AA Data API, LMArena, OpenRouter)
- A2: Snapshot + generator blend (arena + tier + internal bench)
- A3: scorer.py generation-replacement
- A4: Purpose packs + Fugu prior
- A5: CLI fan-out + runtime overlay

**Wave 0: Working-tree disposition**
**Wave 1: Trunk substrate (relay health, continuity fence, GMR telemetry)**
**Wave 2: Governance seams (nexusclaw --live, trust to routing, DG trust fix)**
**Wave 3: nexusctl consolidation + TUI**
**Wave 4: Wiki/DoppelGround neural brain**
**Wave 5: CDP workforce progression**
**Wave 6: Bench v0 + eval pack + SOL remainder**
**Wave 7: Training and hardening (A800 gated)**

### Critical Finding: ModelRelay Scoring Crisis
- 295 deployments in live inventory, approximately 105 online
- **112 rows scored exactly 0.45** — a hard-coded unknown-model default, NOT a benchmark
- GLM-5.2 exists in canonical registry (tier 96) but absent from running npm relay catalogue
- Registry compiler does not generate npm runtime's sources.js or scores.js
- Node relay performs concurrent completion-based health probes, approximately 240 background requests/hour for 60 Mistral aliases alone
- /api/config can expose raw API-key values under wildcard CORS (P0 security defect)

---

## 4. Fable5 — Research Architect and Evidence Policy

### Two Meanings of "Fable5"

**1. Claude Fable 5 (Anthropic Model)**
- Released June 9, 2026 — general-public version of Mythos 5
- Three-layer safety: main model, safety classifiers, Opus 4.8 fallback
- Less than 5% of sessions trigger fallback; 30-day mandatory retention
- Project Glasswing: approximately 150 partners, 10,000+ vulnerabilities found in first month
- Estimated intelligence: approximately 0.95+ (pending Arena validation)
- NOT accessible via free tier — requires Anthropic API subscription/credits

**2. FABLE5 Operational Pattern (NEXUS)**
- Plan then approve then execute workflow
- Recover crashed sessions (work survives in git/plan files)
- Arsenal without ammo (ban dead/junk models)
- 4h model-sync heartbeat (nexus_model_sync_4h.ps1)
- Settings-wipe guard (hard-fail on JSONC parse errors)
- Economics directive (suspend dead baseten lanes, 429-strict on heavy models)

### Fable5 Advisory Logs
| File | Lines | Focus |
|------|-------|-------|
| NEXUSgeneralFABLE5advisorylogs-01.txt | 10,700+ | Registry v3, Node/Python consumer generation, junk model ban, 4h sync, DPO 1000-pair |
| NEXUSgeneralFABLE5advisorylogs-02.txt | 8,000+ | Settings-wipe fix, NIM thinking syntax, DPO monitor milestones, Frontier Intelligence plan |
| NEXUSgeneralFABLE5advisorylogs-03.txt | 3,900+ | 72h gap-closure to M0-M6 milestones, registry v3, S5 candidates, image GuardPlane, A2A evidence gate |
| NEXUSgeneralFABLE5advisorylogs-04.txt | — | 30h grounding advisory, model relay scoring, provider endpoint verification |

### Fable5 Reasoning Deep Dive (from ARCHIVIST)
Fable5 cognitive patterns are structured and execution-oriented:

1. **Context Verification Discipline** — never assumes environment state; runs non-invasive diagnostics first
2. **Deterministic Edge-Case Mapping** — decomposes requests into check-points, maps edge cases before coding
3. **Dual-Layer Code Design** — exposes deterministic interfaces for headless verification
4. **Self-Correction Protocol** — isolate variables, focused reproduction script, pinpoint type mismatch, targeted guard

### Training NEXUS Agents in Fable-like Reasoning
- Diagnostic prerequisite: check binaries, environment, exclude node_modules before any write
- Audit plane: expose /debug/state endpoints for mathematical assertion
- Isolated debug rule: single-purpose reproduction scripts in scratch, deleted after fix

---

## 5. ARCHIVIST Evidence — Full Inventory

### Structure
- **1,590 files** across 16 categories
- **3.2 GB** papers corpus (papers01-13, DATASETs, Workflows)
- Approximately 826 PDFs triaged, approximately 90 deep-read in PAPERS master distillation

### Key ARCHIVIST Documents

#### Fable5/Mythos Analysis
- `fable-5-deep-dive.md` (225 lines) — full technical analysis of Fable 5 and Mythos 5
- `fable5_reasoning_deep_dive.md` (78 lines) — CoT patterns, training directives
- `Claude_Mythos_5_Fable_5_Research_Analysis.md` (337 lines) — 5-part comparative analysis
- `fable5systemprompt.txt` — system prompt extract
- `Claude Fable 5 — System Prompt.txt` — system prompt

#### Frontier Model Intelligence
- `Beyond Scale_ Deconstructing OpenAI's GPT-5.6 Strategy Against Anthropic's Mythos 5 and Fable 5.md`
- `OpenAI GPT-5.6 Sol, Terra, Luna.md`
- `Deep-Dive Audit of GPT-5.6 Sol, Terra, Luna, and the GPT-audit-tools Rumor.md`
- `gpt-5.6-distillation-war-deep-research-2026-06-29.md`
- `GPT56_FABLE_MYTHOS_NEXUS_ASSESSMENT_2026-06-27.md`

#### Model Stack and Training
- `NEXUS OS - Comprehensive Model Curation, Speculative Decoding, and Agent Stacking Dossier.md`
- `NEXUS Core Integration 3.5B Local SLM Stack, 8-Channel Memory, 11-Element Trust, and Fugu-Style Collaborative Intel Distillation.md`
- `NEXUS Scientific Base Fine-Tuning, Merging, and Evolving Stacks.md`
- `Specialized 3.5B Collaborative SLM Stack and Inside-the-Club Governance Plan.md`
- `Liveness Refresher Integration and Rotation Stacks Hardening.md`
- `mistralnewmodelLEANSTRALvibeCLIUltimateGUIDE.txt`

#### Security and Governance
- `ACPultimateGUIDE.txt` — ACP protocol guide
- `ATNITSLOPloopingTOdeadPreventions.txt` — anti-looping prevention
- `GOVERNANCE_VULNERABILITY_SURFACE.md`
- `MCP_VULNERABILITY_ASSESSMENT.md`
- `Confidential Red-Team Diagnostic and Remediation Report for NEXUS OS.md`
- `IMAGE_STEGANOGRAPHY_ATTACK_BRIEF_v1.md` and `v2.md`

#### Anthropic Full Pack
- System cards: Fable 5, Mythos Preview, Opus 4.7
- Security: Data Handling, DLP, Enterprise Security Posture, Key Management
- Research: ExploitGym, STACK adversarial attacks, Pressure Reveals Character
- Policy: Frontier Compliance Framework, UK AISI Alignment Evaluation

---

## 6. NEXUSlogs — Agent Lane Inventory

### Total: 137+ log files in Downloads/NEXUSlogs

### Major Categories

#### Coordination Logs (SOL/TERRA)
- NEXUSnewSOLcoordinationULTRAonCODEXlog-23/24/25.txt
- NEXUSnewTERRAcoordinationULTRAonCODEXlog-26/27.txt

#### Fable5 Advisory
- NEXUSgeneralFABLE5advisorylogs-01/02/03/04.txt

#### Kilocode Orchestrator
- NEXUSkilocodeORCHESTRATORagentlogs-01 through 07.txt

#### OpenCode Backend
- NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-03 through 07.txt
- NEXUSopencodeMAINbackendCODEkimi26log-08 through 15.txt
- NEXUSopencodeMAINbackenddeepseekv4flashlog-16/23/25.txt
- NEXUSopencodeMAINbackendDEEPseekv4PRONIMlog-26/31.txt
- NEXUSopencodeMAINbackendGLM51log-17.txt
- NEXUSopencodeMAINbackendGLM52log-22/24.txt
- NEXUSopencodeMAINbackendGLM52NIMlog-29/32.txt
- NEXUSopencodeMAINbackendgodmodelog-19.txt
- NEXUSopencodeMAINbackendmimo25log-18.txt
- NEXUSopencodeMAINbackendminimaxm3log-20/21.txt
- NEXUSopencodeMAINbackendMINIMAXm3NIMlog-27/28/30.txt
- NEXUSopencodeMAINbackendmistralLEANlabslog-33.txt

#### Grok 4.5 Build (Ubuntu)
- NEXUSbuildubuntuGROK45logs-01 through 07.txt
- NEXUSubuntuGROKbuildlogs-01.txt
- NEXUSubuntuHERMESlog-01 through 08.txt

#### Model Research
- NEXUSbenchmarkMODELresearchlog-01 through 08.txt
- NEXUSmodelrelaymonitortestlog-01/02/03.txt
- NEXUSmodelRELAYrouterlogs-01.txt

#### Browser/Visual
- NEXUSvisualweaverGPT55browsermcplogs-01.txt
- NEXUSvisualweaverGROKbrowsermcplogs-01.txt
- NEXUSvisualweaverLOGS-01/02.txt
- NEXUSweaverIMAGINElabGLMlogsMIXED-01.txt

#### A2A / Collaboration
- NEXUScloudcompZOconversationlog-01.txt
- NEXUScloudcompZOconversationSLACKlog-01.txt
- NEXUSteamRESEARCHandDEVlogs-01.txt

#### V4 Planning (Codex)
- NEXUSv4planningCODEXlog-01 through 22.txt

---

## 7. Live Repository State

### Branch: codex/specimba/CODEX_SOLv1 (HEAD 61c4bfae)
- 129 commits ahead of main
- Built on top of nexus-core-solidify (ends at a6c3c6f3)
- Identical to opencode continuity-substrate branch tip — the three-way branch collision is mechanically resolved at fd81a4e0

### Working Tree
- Approximately 46 modified files, approximately 37 untracked paths
- Three uncommitted buckets:
  1. MiniMax M2.7/M3 license flip (registry + generated mirror) — M0 item 1, ready to commit
  2. Multi-lane A2A/CDP bundle (7 new .mjs tools, 3 new MCP tools, anti-theatre guard)
  3. Sentinel-native 18-file slice (UiPath salvage, broken import)

### Port Plane (Canonical)
| Port | Owner | Status |
|------|-------|--------|
| 7350 | Node ModelRelay primary | UP, 237 catalogue rows, but 112 at 0.45 fallback |
| 7352 | Brain API / governance | Healthy |
| 7354 | Grok MCP bridge | 25 tools, 2.4.0-p0-continuity |
| 7355 | Python ModelRelay fallback | UP but all 3 health targets false |
| 7356 | Dashboard / arena | UP, 295 rows flat display |
| 7357 | God Mode proxy | 236 catalogue rows, 0 verified up |
| 7358 | Duplicate MCP | Retire after 7354 soak |
| 9224 | Chrome CDP multi-lane | Currently non-responsive |

### Test Status
- 403/403 security tests green (per 01_PROJECT_STATE.md)
- 17/17 OpenCode-focused tests green
- 83/83 Grok port/GMR tests green
- 66 A2A governance tests green
- 170 GMR tests green
- 120 relay tests green
- 95/95 registry/relay/dashboard tests green
- 36/36 grounding tests green
- Full suite: 4100+ tests historically green

---

## 8. The Eight Golden Findings (PAPERS Master Distillation)

From docs/research/PAPERS_MASTER_DISTILLATION_2026-07-10.md (commit 61c4bfae):

1. **Harness beats weights** — LIFE-HARNESS: +88.5% improvement from frozen models by evolving the interface; transfers across 17 backbones
2. **Training pipeline is the attack surface** — Virus shows guardrail-filtered data still carries safety-breaking payloads; FCV shows code can pass all tests and still ship vulnerabilities
3. **Teacher-free, trace-native training is the A800 play** — SERA (26x cheaper than RL), RFT-first, GRPO later; RIFT reward-weighting means failed traces stop being wasted
4. **Trust ledger is a reward signal** — RIFT reward weight is our Beta posterior; Fugu soft-target SFT is now unblocked
5. **Calibrate judges before they gate** — VerifyBench/PPE/PGED; even frontier judges produce 64% cyclic preferences
6. **Memory needs lineage** — MemLineage drives memory-laundering attacks to 0 ASR at sub-ms cost; LightMem sleep-time consolidation runs on idle free quota
7. **Browser-agent security is mature** — PACT/AuthGraph/ARGUS all beat the CaMeL baseline our M5 plan assumed
8. **Free lunches for the 8GB lane** — min-p/p-less samplers, TOOLSPEC (3.5-4x speedup on tool-call JSON), Token Recycling, 270M micro-specialists trainable on the 4070

---

## 9. Seven Severed Integration Seams

1. **Registry to live scorer**: npm relay on :7350 reads neither models.registry.json nor scorer.py; Python and TS score sources have diverged (53 vs 70 models)
2. **Routing telemetry to nowhere**: Chimera/LG produce stability reports that nothing persists or consumes
3. **Nexusclaw execution is dry-run-gated**: approved envelopes never execute through a governed path
4. **Wiki dossiers are flat**: frontmatter but no wikilinks; two separate wiki roots
5. **Bench trust ledger never feeds routing**: scores do not loop back
6. **Three CLI packages with stranded unique commands**: nexusctl/, nexus_os/cli/, nexus_cli_ctl/
7. **HERMES API-routing and CDP browser share no task envelope**: handoff via shell scripts

---

## 10. Model Stack (Grounded from antiGRAV-11 + FABLE5 + Milestones)

### Local Stack (8GB VRAM ceiling)
| Tier | Role | Model | Size |
|------|------|-------|------|
| T0 | Intent classification | FunctionGemma-270M | ~350MB |
| T0 | Command poison check | BashGemma-270M | ~400MB |
| T0 | Embeddings | nomic-embed-text-v1.5 | ~80MB |
| T1 | VATS gatekeeper | Llama-Guard-3-1B | ~1GB |
| T1 | Pre-filter classifier | Gemma-3-1B heretic | ~1GB |
| T2 | Math/code (uncensored) | Mythos-nano-OBLITERATED | ~2.5GB |
| T2 | Multi-turn tool-caller | refinedtoolcallv5-3b | ~2.5GB |
| T2 | Coding specialist | VibeThinker-3B-Agentic | ~2.5GB |
| Heavy | Safety confirmation | Nemotron Safety Guard 8B Q4 | ~4.92GB |

### Cloud Stack (via ModelRelay)
| Provider | Model | Context | Status |
|----------|-------|---------|--------|
| kilocode | z-ai/glm-5.2 | 1M | Free reasoning primary |
| opencode | deepseek-v4-flash-free | 1M | Fast tier |
| kilocode | nvidia/nemotron-3-ultra-550b:free | 1M | 550B MoE |
| nim | minimaxai/minimax-m3 | 512K | Serial-only, 429-prone |
| nim | qwen/qwen3.5-122b-a10b | 122K | NIM-only |
| kilocode | moonshotai/kimi-k2.7-code | 262K | Code specialist |
| LongCat | LongCat-2.0 | 1M | 128K output |
| InternAI | intern-s2-preview | 256K | Thinking mode |

### Guard Cascade (L0-L4)
| Level | Model | Size |
|-------|-------|------|
| L0 | BashGemma 270M | ~400MB |
| L1 | FunctionGemma 270M | ~350MB |
| L2 | GLiGuard-300M | ~500MB |
| L3 | arch-guard-300M | ~600MB |
| L4 | Meta-attack detector (regex, 46 categories) | 0 |
| Heavy | gemma4-e2b-guard | 2.3B / 1800MB |
| Heavy | gemma2-2b-abliterated | 2.0B / 1400MB |

---

## 11. D: Disk Asset Inventory

### Key Directories
- D:\NEXUS_MODELS — gguf/safetensors/loras/benchmarks/datasets
- D:\ollama_models — Ollama model store
- D:\MyModels — Additional model blobs
- D:\safetensors_candidates — Guard model candidates
- D:\BACKUPS — System backups
- D:\NEXUS_COLD — Cold storage
- D:\NEXUS_RECOVERY — Recovery snapshots (NEXUS_20260605_140529)
- D:\Ollama_Backup — Ollama backup
- D:\GROSS — GROSS forensic evidence
- D:\NEXUS_OS_AUDIT — Audit artifacts
- D:\cache — Cache

### Verified Local Assets
- VibeThinker-3B Q4 (at D:\NEXUS_MODELS\gguf)
- VibeThinker-1.5B Q4
- DeepSeek-R1-Distill 1.5B Q4
- Qwen2.5-Coder 1.5B Q4
- Nemotron Safety Guard 8B Q4 (~4.92 GB)
- Function-calling datasets staged (xlam, glaive, APIGen, hermes)
- DoppelGround.zip origin backup

### D:\NEXUS_MODELS\benchmarks — EMPTY (bench substrate needs construction)

---

## 12. Known Blockers (Honest Inventory)

| ID | Blocker | Severity | Owner |
|----|---------|----------|-------|
| B1 | :7354 elevated stale process | P0 | Admin terminal |
| B2 | Cloud _check_health posts to Ollama for cloud models | P0 | Codex exec |
| B3 | DPO judge still intern-s2-preview should be deepseek-v4-pro | P0 | Codex exec |
| B4 | Three-lane collision on continuity substrate | P0 | Resolved at fd81a4e0 |
| B5 | Ollama reinstall / llama-server router (M1) | P1 | Admin + plan |
| B6 | Brain API / 7350 health regressions intermittent | P1 | Doctor scripts |
| B7 | Qwen WebDev not always in Preview mode | P2 | CDP lane task |
| B8 | Claw hard CASE bank deferred | hold | Operator |
| B9 | ~60+ unstaged multi-lane files | P1 | Git hygiene sprint |
| B10 | 01_PROJECT_STATE partially stale | P2 | Refresh after exec |
| B11 | 112/295 models at 0.45 fallback score | P0 | Track A |
| B12 | CDP 9224 currently non-responsive | P1 | Grok lane |
| B13 | GuardPlane service source path mismatch | P1 | Investigation |
| B14 | Duplicate MCP on 7358 | P1 | Retire after 7354 soak |
| B15 | Grounding scan --changed-only liveness defect | P0 | Doctor fix |
| B16 | /api/config exposes raw API keys under wildcard CORS | P0 | Security fix |
| B17 | Node relay concurrent completion-based health storms | P0 | Runtime fix |
| B18 | Hermes bypasses NEXUS with direct NVIDIA on Windows | P1 | Route through 7350 |

---

## 13. Agent Lane Assignment (Verified)

| Lane | Role | Verified Work | Open Items |
|------|------|---------------|------------|
| FABLE5 | Research architect, scientific claim-gate designer | Registry v3, trace partitioning, Trust Ledger, A2A evidence gate, relay refresher, benchmark replay, vision guard, papers master distillation | Solidify-the-Tree stopped at quota; ~826-PDF coverage not independently reproduced |
| OpenCode | Continuity, CLI, registry compiler, client sync | Memory/intel/continuity commands, 1206 tests green, NIM truth rooted (8 RPM, MiniMax KV warm-up, GLM-5.2 DEGRADED) | Existing continuity ledger incompatible; CLI drops payloads; no lock/fsync |
| Grok 4.5 | Runtime adapters, MCP/CDP, browser evidence, ports | Port plane 7350-7360 fix, GMR/Chimera pipeline, CDP hardening, MCP 25 tools, Intern A100 GPU smoke | Shared-branch collision; browser success heuristics unsafe; MCP partly uncommitted; Intern HARD_STOP |
| Kilocode | Governance brain, grounding policy | GND-001, GAP_ANALYSIS, M0 corrections, fabrication catch | — |
| Codex/SOL | Integration, schemas, branch leases, verification | SOL plan, PR #52 repair plan, P0 backlog | Plan only; no execution before rate limit |
| Hermes | ACP reference client | WSL config, model_sync, managed YAML | Direct NVIDIA bypass on Windows; duplicate providers |
| Qwen | Preview DOM evidence lane | DOM recon maps in ARCHIVIST | Needs Preview-DOM success criterion |
| Intern | Human-driven GPU benchmark/training | A100 smoke via CDP (tick 17 verified) | HARD_STOP; no automatic restart |

---

## 14. Security Flags (Rotation-Only)

In descending severity:
1. Operator-pasted plaintext Kimi/Groq/OpenRouter keys (+~10 more) in HERMESlog-07 ~L5273-5303
2. LongCat ak_ key in plaintext on line 1 of ARCHIVIST LongCat guide
3. InternAI sk_ key + Bearer tokens in ARCHIVIST InternAI guide
4. Archive zip passphrase in zocomputer log-02
5. 7352 weak auth on 0.0.0.0
6. Past ngrok exposure of 7354
7. /api/config exposes raw API key values under wildcard CORS

---

## 15. Recommended Next Steps (Priority Order)

### Immediate (P0)
1. **ModelRelay containment**: Stop completion-based health storms; replace with provider-level GET /models; zero inference during startup
2. **Scoring v2**: Remove 0.45 fallback; inject arena scores from AA/LMArena/OpenRouter; generate all artifacts from one registry
3. **Security fix**: /api/config returns key fingerprint only; replace wildcard CORS; add CSP
4. **Hermes routing**: Route through 7350; direct providers become governed break-glass fallbacks
5. **Grounding scan fix**: Resolve --changed-only liveness defect
6. **Continuity fence**: Browser/MCP rows capped at UNVERIFIED/E0

### Short-term (P1)
7. **MCP 25-tool parity**: Sync all surfaces to 25 tools; retire duplicate 7358
8. **A2A evidence gate**: Wire to Grok to Qwen Preview path; re-run 9-lane cycle
9. **nexusctl consolidation**: Three packages to one; add TUI
10. **Wiki/DoppelGround**: Consolidate to one Obsidian vault; fix trust-90.0 bypass
11. **D: benchmark skeleton**: Create before any local-model promotion

### Medium-term (P2-P4)
12. **Bench v0**: 5 deterministic tasks; frozen eval pack; judge calibration
13. **Local stack**: llama-server router mode decision; bench-off Nanbeige vs VibeThinker
14. **Training flywheel**: SERA, CLEANER, RIFT, Fugu SFT, guard-DPO
15. **Memory lineage**: MemLineage full build; 8-channel vault consolidation
16. **Browser security**: PACT/AuthGraph/ARGUS; WASP/RedTeamCUA regression suites

---

## 16. References

### Canonical Plans
- docs/plans/NEXUS_CODEX_GPT56_SOL_ULTIMATE_GROUNDING_AND_MASTER_PLAN_2026-07-10.md
- docs/plans/NEXUS_MODEL_USAGE_PLAN_2026-07-10.md
- docs/plans/NEXUS_MILESTONES_2026-H2.md
- docs/research/PAPERS_MASTER_DISTILLATION_2026-07-10.md
- docs/research/STEP_3_7_FLASH_GROUNDING_REVIEW_2026-06-18.md
- docs/research/NEXUSCLAW_DESIGN.md

### Key Logs (Primary Evidence)
- NEXUSnewSOLcoordinationULTRAonCODEXlog-23.txt (18,195 lines)
- NEXUSnewTERRAcoordinationULTRAonCODEXlog-26.txt (10,759 lines)
- NEXUSkilocodeORCHESTRATORagentlogs-01.txt (1,414 lines)
- NEXUSgeneralFABLE5advisorylogs-01.txt (10,700+ lines)
- NEXUSantiGRAVnexlog-11.txt (12,478 lines)

### ARCHIVIST Dossiers
- fable-5-deep-dive.md (225 lines)
- fable5_reasoning_deep_dive.md (78 lines)
- Claude_Mythos_5_Fable_5_Research_Analysis.md (337 lines)
- ARCHIVIST_INDEX.md (1,761 lines)
- ARCHIVIST_PAPERS_DOSSIER_v1.md / v2_DEEP.md / v3_TEMPORAL.md

---

Report generated: 2026-07-13 19:22 UTC
Grounding coverage: Downloads/NEXUSlogs (137+ files), Downloads/ARCHIVIST (1,590+ files), Documents/NEXUS (live repo), D:\ (cold storage)
Methodology: Full read of mandated documents, targeted reads of key logs, live port verification, git ancestry checks, D: disk inventory, parallel agent grounding
