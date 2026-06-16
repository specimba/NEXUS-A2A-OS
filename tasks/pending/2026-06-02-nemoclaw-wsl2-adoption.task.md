<!-- CANARY: nemoclaw-wsl2-lane-a-2026-06-02 -->
---
id: 2026-06-02-nemoclaw-wsl2-adoption
title: [Lane A] NemoClaw v0.0.55 WSL2 Adoption - Reconcile
priority: P0
status: pending
created: 2026-06-02
lane: A
scope: external-layer, governance
---

## Lane
**Current Lane:** A (Reconcile)  
**Previous Lane:** (none)

## Goal
Document the current state, decision, and gap for adopting NVIDIA NemoClaw v0.0.55 as the runtime for the 3 OsmanClaw swarm agents (orchestrator / reviewer / researcher-ops) inside the user's WSL2 Ubuntu 26.04 environment, layered under NEXUS governance (KAIJU / VAP / 5-track memory).

## Evidence / Reconcile Document
- **Primary decision artifact**: `research/intake/2026-06-nvidia-spark-nemoclaw-nexus-decision.md` (125 lines, 15040 bytes, 2026-06-02 15:15)
  - Inspects all 18 NVIDIA Spark links: nemoclaw, openclaw, hermes-agent, playbooks, applications, connect-to-spark, multi-agent-chatbot, cli-coding-agent, unsloth, connect-two-sparks, isaac, speculative-decoding, llama-cpp, nim-llm, vllm, lm-studio, multi-modal-inference, open-webui, nemo-fine-tune, dgx-dashboard
  - Compares NemoClaw (NVIDIA security wrapper on OpenClaw + OpenShell) vs plain OpenClaw
  - Decision: **Adopt NemoClaw (OpenClaw base + OpenShell + Hermes support)** as the runtime. Keep NEXUS as the coordination/governance layer (KAIJU top gate, VAP audit, 5-track memory via MCP, TokenGuard budgets).
- **Feasibility verification**: `research/intake/2026-06-02-nemoclaw-wsl2-feasibility.md` (2026-06-02 20:50)
  - WSL2 Ubuntu 26.04 LTS, x86_64, kernel 6.6.87.2-microsoft-standard-WSL2
  - Docker 29.5.2 (Runtimes: `io.containerd.runc.v2 nvidia runc`)
  - GPU: RTX 4070 Laptop GPU, Driver 596.49, CUDA 13.2
  - Verified `docker run --rm --gpus all ubuntu:24.04 nvidia-smi` works (2026-06-02 20:50)
  - Prereqs all YES: NemoClaw supports DGX Spark OR RTX PC/laptops, x86_64 confirmed, OS version forward-compat
- **Executable install plan**: `D:\GROSS\phase3\plans\NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md` (8 steps, 4 pre-install decisions resolved)
  - D1: Ollama port 11436 (NEXUS uses 11434 primary, 11435 guard tier)
  - D2: Model qwen2.5:7b (already cached, 4.5GB, skip 20GB qwen3.6:35b default)
  - D3: WSL2 systemd watchdog (optional, defer if systemd not enabled)
  - D4: NEXUS MCP egress to 127.0.0.1:7354
- **Patched ZO plan**: `C:\Users\speci.000\Documents\NEXUS\NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` (21449 bytes, 318 lines, 2026-06-02 15:16)
  - 4-layer stack: Tailscale L1, MCP L2, A2A L3, **NemoClaw L4** (was OpenClaw L4)
  - 3 OsmanClaw agents: orchestrator #nexus-control, reviewer #nexus-codex-tasks, researcher/ops
  - Flow: Slack/Zo → KAIJU gate → NemoClaw/Hermes execution in sandbox → VAP log → memory update
  - Phases 0-4, with Phase 0 = install NemoClaw+Hermes via playbooks

## Cross-Reference to NEXUS Master Plan v4

The Master Plan v4 (NEXUS_OS_V4_MASTER_PLAN.md, 56KB) calls out gaps that NemoClaw directly addresses:

| Master Plan Gap | NemoClaw Solution |
|-----------------|-------------------|
| §2.2 #1 "No agent sandbox isolation" | OpenShell Landlock + seccomp + netns per sandbox |
| §2.2 #3 "No cross-agent prompt injection protection" | OpenShell network policy + filesystem isolation |
| §2.2 #5 "No E2E encryption" | NemoClaw local-first, no cloud exfiltration by default |
| §4 "Sandbox Architecture: Multi-Tier Isolated Execution" | NemoClaw = exact fit for Linux execution tier |
| §5 "Cross-Agent Security: Terminal Poisoning + Prompt Injection" | NemoClaw sandbox isolation defends terminal poisoning |
| §11 "Code Reconciliation: NEXUS Main + HERMES Swarm Pack" | NemoClaw/OpenShell unifies the 3-pillar architecture |
| §12 "Deployment Tiers & Platform Strategy" | NemoClaw fits WSL2 / RTX PC tier |

## Constitutional Alignment (NEXUS_CONSTITUTION.md v0.5, 2026-06-01)

- **Invariant 1 (Governance Before Execution)**: PRESERVED — NEXUS KAIJU is the top gate; NemoClaw agents only execute after KAIJU approval
- **Invariant 2 (Single Source of Truth for Governance State)**: PRESERVED — TrustKernel + VAP + 5-track Vault remain canonical; NemoClaw may consume/cache but not override
- **Invariant 3 (Evidence-Grounded Decisions)**: SATISFIED — 15KB decision doc + feasibility verification + install plan all backed by WebFetch, WSL probes, file inspection
- **Invariant 4 (Proposal-Bound + Test-Gated)**: THIS TASK is the proposal; Lane A complete, Lane B/C follow
- **Invariant 5 (Auditability)**: PRESERVED — VAP recording planned for all NemoClaw sandbox registrations + actions

## Activation Lane Requirement

NemoClaw adoption is **significant HOLD-state work** (NEXUS_AGENT_PROTOCOL.md v2.0 §1: "Integrating external layers"). Per `docs/governance/ACTIVATION_LANES.md`:
- Lane A (Reconcile): **THIS TASK** — current state + gap + decision documented
- Lane B (Active Diagnosis): NEXT — bounded diagnostic install of NemoClaw on WSL2 (does it actually work? what breaks? what config tweaks needed?)
- Lane C (Isolated Candidate): AFTER B — full NEXUS MCP bridge wired to 3 NemoClaw sandboxes, KAIJU-gated end-to-end test

## Required Work (Lane A — THIS TASK)

1. ✅ Inspect all 18 NVIDIA Spark links (WebFetch)
2. ✅ Compare NemoClaw vs OpenClaw on 6 axes
3. ✅ Adopt NemoClaw for OsmanClaw swarm runtime
4. ✅ Verify WSL2 environment prereqs (GPU, Docker, OS, Node)
5. ✅ Resolve 4 pre-install decisions (port, model, watchdog, MCP egress)
6. ✅ Write executable install playbook (8 steps)
7. ✅ Cross-reference with NEXUS master plan v4 + constitution
8. ⏳ Create this task file (in progress)

## Exit Condition (Lane A)

- [x] Single, agreed "Reconcile Document" exists (`2026-06-nvidia-spark-nemoclaw-nexus-decision.md`)
- [x] No unresolved factual disputes (all evidence grounded in WebFetch, WSL probes, file inspection)
- [x] Pre-install decisions resolved
- [x] Executable install plan with rollback
- [x] Cross-referenced with NEXUS master plan + constitution
- [x] Task file created with proper lane metadata

**Lane A: COMPLETE. Ready for Lane B (Active Diagnosis) — bounded NemoClaw install on WSL2.**

## Verification Gate

- All claims evidence-grounded (file paths, line numbers, WebFetch URLs, WSL probe outputs)
- 4 pre-install decisions documented with rationale
- No fabrication; all facts verified by direct disk/WSL/WebFetch inspection
- Cross-references with NEXUS master plan + constitution preserved

## Boundaries

- **NOT** moving out of HOLD state yet (Lane B starts with bounded install)
- **NOT** deploying 3 sandboxes yet (Lane C)
- **NOT** committing changes to canonical NEXUS branches (Lane A is reconcile-only)
- **NOT** modifying NEXUS TrustKernel / Guard Plane / VAP code (Lane C is for that)
- **Respect** AGENTS.md Continuous Autonomous Operation Rules (no user prompts mid-flow except at real decision points)
- **Respect** existing "not allowed yet" lists (e.g., don't claim cryptographic VAP, full A2A, OWASP ASI maturity)

## Next Lane

**Lane B (Active Diagnosis)**: Execute Steps 0-2 of the install plan (pre-flight, pre-pull Ollama, install NemoClaw v0.0.55 via `curl -fsSL https://www.nvidia.com/nemoclaw.sh | NEMOCLAW_INSTALL_TAG=v0.0.55 bash`). Bounded: stop after install + single sandbox creation. Stop rules: (a) if cgroup fix needed, (b) if Node.js install fails, (c) if Ollama port conflict unresolvable, (d) if model download fails, (e) any safety halt. Each stop writes a halt report. **Requires user approval to proceed to Lane B** (per user's "C - A - B" order = continue ingestion → execute install → surface results).

**Lane C (Isolated Candidate)**: After Lane B success, create 2 more sandboxes, wire NEXUS MCP bridge, full KAIJU-gated end-to-end test, VAP log integration. Promotion criteria: 3 sandboxes healthy, MCP egress policy verified, KAIJU gate returns correct ALLOW/DENY, VAP records created.

## Open Questions (for Lane B / C, not Lane A)

1. Will NemoClaw v0.0.55 work on WSL2 with Ubuntu 26.04 (only 24.04 is "expected" per README)? → Bounded test in Lane B.
2. Does OpenShell sandbox survive WSL2 sleep/resume? → Watchdog test in Lane C.
3. Can 3 NemoClaw sandboxes share one WSL2 GPU without OOM? → Memory test in Lane C.
4. Does NEXUS KAIJU via MCP add meaningful latency to NemoClaw agent calls? → Latency test in Lane C.
5. Does the NemoClaw network policy correctly block exfiltration (the GROK 39GB scenario)? → Penetration test in Lane C.

## Reference Files

- `C:\Users\speci.000\Documents\NEXUS\NEXUS_OS_V4_MASTER_PLAN.md` (56KB, sections 4-7, 11-12)
- `C:\Users\speci.000\Documents\NEXUS\docs\governance\ACTIVATION_LANES.md` (44 lines)
- `C:\Users\speci.000\Documents\NEXUS\docs\governance\NEXUS_CONSTITUTION.md` (62 lines)
- `C:\Users\speci.000\Documents\NEXUS\NEXUS_AGENT_PROTOCOL.md` (68 lines)
- `C:\Users\speci.000\Documents\NEXUS\NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` (318 lines, patched 2026-06-02)
- `C:\Users\speci.000\Documents\NEXUS\research\intake\2026-06-nvidia-spark-nemoclaw-nexus-decision.md` (125 lines, 15040 bytes)
- `C:\Users\speci.000\Documents\NEXUS\research\intake\2026-06-02-nemoclaw-wsl2-feasibility.md` (newly created)
- `D:\GROSS\phase3\plans\NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md` (executable playbook)
- `C:\Users\speci.000\Documents\NEXUS\01_PROJECT_STATE.md` (canonical state, 186 lines)
- `C:\Users\speci.000\Documents\NEXUS\knowledge.md` (canonical knowledge base, 182 lines)
- `C:\Users\speci.000\Documents\NEXUS\docs\gross\GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026-05-31.md` (GROSS context, 408 lines)
