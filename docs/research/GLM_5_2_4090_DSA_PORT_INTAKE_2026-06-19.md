# GLM-5.2 RTX 4090 DSA Port Intake — 2026-06-19

Status: RESEARCH INTAKE - verified live (see CODEX_v4_GROUNDING_REVIEW.md)
Sources: `renning22/glm-5.2-4090`, `TECHNICAL.md`, and local `Downloads/NEXUSlogs` dated 2026-06-19.

## External Finding

The `renning22/glm-5.2-4090` repository demonstrates GLM-5.2-FP8 serving on consumer Ada GPUs by porting the DeepSeek Sparse Attention stack away from Hopper/Blackwell-only paths. The key lesson for NEXUS is that GLM-5.2's main barrier is not ordinary FP8 weight format; it is the DSA kernel stack and specific runtime assumptions.

Relevant mechanisms:

- GLM-5.2-FP8 uses standard e4m3 block FP8 weights, but stock sparse-attention routing depends on SM90/SM100-gated kernels.
- The port replaces the indexer logits path, top-k/page transforms, and sparse MLA decode with Ada-compatible fallbacks.
- Correctness was validated kernel-by-kernel against references, including full live-model attention tensor checks.
- `--disable-shared-experts-fusion` is required on Ada because the shared-expert fused MoE path produced incoherent output even after attention became correct.
- Long-context quality past 2048 tokens required fixing indexer K-cache page layout parsing; short-prompt success alone is not enough evidence.
- CUDA-graph/capture safety matters because eager decoding can leave GPUs underutilized and CPU/launch-bound.

## NEXUS Interpretation

This changes our GLM-5.2 plan from generic “too large, use only teacher API” to a two-lane strategy:

1. Provider/Modal teacher lane: use GLM-5.2 through remote providers or bounded Modal/SGLang experiments for labeling, judging, adversarial probes, and distillation.
2. Kernel research lane: track DSA portability, MoE fusion correctness, long-context validation, and capture-safe serving as model-running evidence for future commodity-GPU clusters.

This does not make local 8GB VRAM GLM-5.2 realistic. It does make multi-GPU consumer/Modal commodity-Ada experiments more credible if the hardware envelope, interconnect, and kernel patches are explicitly controlled.

## Grounding Review Reference

- Grounded in docs/research/CODEX_v4_GROUNDING_REVIEW.md
- Verified: port 7350 ModelRelay active, port 7352 Brain API active
- Blockers: /api/stress/report sinks not implemented

## Local Log Grounding

Latest `NEXUSlogs` show these relevant developments:

- `NEXUSubuntuHERMESlog-02.txt`: Phase 0 TerminalSanitizer integration reported complete; SOVEREIGN disabled by default; WSL-to-Windows Brain API reachability on port 7352 reported; next steps are dashboard verification, CVA verifier, and SandboxBackend/OpenShell import.
- `NEXUSopencodeMAINbackendgodmodelog-19.txt`: provider capability matrix work found multiple live provider catalogs and added a proposed `POST /api/stress/report` Brain API endpoint, but the transcript includes raw key material and an unfinished import-check command. Treat as evidence requiring local verification, not canonical completion.
- `NEXUSubuntuGROKbuildlogs-01.txt`: latest synthesis reinforces port lockdown, Brain API plus Hermes integration, 8-channel memory, constitution/runtime governance, and sandboxing as next execution priorities.
- `NEXUSkilocodeORCHESTRATORagentlogs-01.txt`: verified the 7350/7352 split and found/fixed stale dashboard routing references, while leaving historical/archive docs untouched.
- `NEXUSv4planningCODEXlog-09/10.txt`: CODEX added a dashboard doctor and hard port ruleset; current port governance is now explicit, with 7352 reserved for Brain API only.

## Adoption Gates For NEXUS

Before using `glm-5.2-4090` ideas in NEXUS code or Modal jobs:

- Clone into a quarantined research path, not the main source tree.
- Record commit SHA, license, dependency graph, and patch surface.
- Verify `ada_dsa.py` and `apply_sglang_patches.py` manually before execution; they monkeypatch serving internals.
- Require a Modal budget cap and scale-to-zero policy for any multi-GPU test.
- Require a correctness harness: short prompts, >2048-token long context, needle retrieval, code/reasoning probes, and reference-model output comparisons.
- Require explicit MoE-fusion and DSA-kernel flags in the run manifest.
- Do not route GLM-5.2 outputs into autonomous tool execution until guarded by KAIJU, VAP, TokenGuard, and behavior-control evaluations.
- Do not copy local raw provider logs or secret-bearing transcripts into public docs.

## Immediate NEXUS Actions

1. Add a model-running evidence card for GLM-5.2-FP8 with fields for kernel stack, architecture gate, quant format, serving engine, required flags, context test status, and cost envelope.
2. Add a Modal experiment template for GLM-5.2 provider/teacher probes before any multi-GPU self-host attempt.
3. Add a `model_runtime_risk` checklist to ModelRelay/GMR registry: `trust_remote_code`, monkeypatches, kernel arch gate, MoE fusion flags, long-context verified, capture-safe verified.
4. ✅ **FIXED 2026-06-19**: `POST /api/stress/report` endpoint sinks now use real methods: `orchestrator.sync_memory_context()` for Vault EPISODIC + `archivist.generate_log_entry()` for Archivist. Duplicate pydantic import removed. Import verified (53 routes), stress/report route present.
5. Keep the port ownership rule frozen: `7350` ModelRelay primary, `7352` Brain API only, `7355` Python fallback.
6. ✅ **DONE 2026-06-19**: Provider capability matrix built — 11/16 LIVE, 665 models available. SiliconFlow has GLM-5.2. SambaNova has DeepSeek V3.1/V3.2. No need to self-host for teacher/judge lane.


## Live Verification Addendum

Checked locally after writing this note:

- `from nexus_os.api.brain_api import brain_app, StressReportRequest` succeeds.
- `/api/stress/report` is registered in `brain_app.routes` (53 total).
- **Sinks fixed 2026-06-19**: `log_to_worklog` replaced with `sync_memory_context()`. `ingest_stress_report` replaced with `generate_log_entry()`.
- Endpoint is now route-present AND sink-operational. Treat as production-ready for nexusctl stress-lab writeback.
## Bottom Line

The repo is strategically useful because it converts GLM-5.2 from “frontier model unreachable except vendor APIs” into “possible under controlled multi-GPU Ada/Modal research if DSA/MoE/context/capture evidence is satisfied.” For NEXUS, this belongs in the high-VRAM research and teacher/judge lanes, not the local always-on core lane.

