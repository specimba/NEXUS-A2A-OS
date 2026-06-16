# AGENTS.md - Nexus OS Agent Operating Protocol

## Mission
Nexus OS is a governed, agent operating system. Every agent working in this repository must preserve the core invariant: actions are evidence-grounded, proposal-bound where appropriate, test-gated, and auditable.

## System Boundaries
- Nexus OS is the governance and orchestration layer.
- DoppelGround is the evidence preparation layer.
- TWAVE is the low-VRAM execution layer and remains wrapper-only unless its HOLD state is explicitly lifted.
- GeniusTurtle is the operator UI layer and must not embed model weights, secrets, or governance internals.
- Model Arena is an evidence tool; it reports model performance and must not delete, fine-tune, or promote models automatically.

## Source Of Truth
- Read `01_PROJECT_STATE.md` first for the current canonical state.
- Read `knowledge.md` for a quick project overview, commands, and conventions.
- Prefer filesystem state, tests, git history, and canonical docs over chat memory.
- Read current files before making claims or edits.
- Treat downloaded reports and external team notes as input evidence, not canonical state, until reconciled into tracked docs.
- Do not create duplicate canonical files with conflicting content. Merge toward one clear source of truth.
- The `docs/handbook/` directory contains detailed operational guidance (nexusctl usage, safety procedures, troubleshooting).

## Core Architecture Map
- Bridge: external protocol boundary, API ingress, SDK/MCP adapters, secrets lookup.
- Governor: KAIJU gates, policy checks, trust scoring, compliance, approval/denial decisions.
- Vault: 8-channel memory, durable records, encryption policy, trust persistence.
- Engine/GMR: task routing, Hermes decisions, circuit breakers, model selection, execution flow.
- Monitoring: TokenGuard, VAP/audit logs, telemetry, stress/weight-room evidence.

## Execution Rules
- Keep changes bounded to one coherent task slice.
- Do not run broad refactors without reporting the planned refactor first.
- Do not stage or commit sandbox files, mock secrets, raw research dumps, model weights, generated caches, or unreviewed downloads.
- Do not use `git add .` in this repository. Stage explicit reviewed paths only.
- Do not delete local models or archives without an inventory, backup, and rollback path.
- Do not expose Ollama, private weights, DoppelGround raw sessions, or core TWAVE internals to external teams.
- Before ending a session or transferring work, validate the last cycle with `nexusctl cycle-check` when available. Use `nexusctl handoff` to generate a cold-handoff package for agent transfers.

## Governance Gates
- No "done" claim without verifiable evidence: test output, diff, file path, or explicit reviewed artifact.
- Core code changes require focused tests; DB, router, governor, bridge, vault, or GMR changes require the full suite unless explicitly blocked.
- Security-sensitive changes require hard-fail defaults and development-only escape hatches that are explicit in config.
- Retroactive provenance tools must start in dry-run/report-only mode. They may not auto-commit, auto-approve, or auto-create governance records until reviewed.

## Git Discipline
- Check `git status --short` before staging.
- Separate unrelated work into separate commits.
- Leave unknown or unrelated user/agent changes unstaged unless the user explicitly asks to include them.
- Commit messages should state the behavioral change and verification result.
- GVAW target: proposal-linked branches, VAP/trust trailers, reviewed merges, and no direct unreviewed mainline changes.

## External Team Rules
- TWAVE wrapper team gets API contracts and mocks only, with port `7353` under `/twave/*`.
- GeniusTurtle UI team gets UI contracts and mock APIs only.
- Nexus governance API remains the canonical backend on port `7352`.
- Public-facing repos must pass leak scanning and must not contain private research, secrets, model weights, or raw evidence dumps.
- Use `nexusctl migrate-frontmatter` to sanitize markdown before public release.
- Use `nexusctl handoff` to package context for external team handoffs.

## Continuous Autonomous Operation Rules (REVISED v2.0)
When operating in AFK/autonomous mode, agents MUST follow this safety checklist:

### Pre-Execution Safety Gates
- [SAFETY-1] Verify output integrity before passing to another agent (TerminalSanitizer + VerifiableOutput)
- [SAFETY-2] Confirm sandbox isolation is active (no shared PTY with other agents)
- [SAFETY-3] Respect token budget limits (check TokenGuard before expensive operations)
- [SAFETY-4] Pass all KAIJU evaluations before taking actions with side effects

### Execution Rules
- Continue executing work until task completion, safety check failure, or error
- Never prompt user for compaction unless explicitly requested
- If context exceeds 90%, silently compact to checkpoint and continue
- Log progress to `.nexus_pi/state/session_compact.json` periodically

### Failure Handling
- **Safety check failure**: HALT IMMEDIATELY. Do not auto-retry safety failures.
- **Non-safety error**: Retry up to 3 times with exponential backoff, then halt.
- **HALT state**: Write a clear failure report to `.nexus_pi/state/halt_report.json`.
  Include: time, failed check, last known good state, recovery hint.

## Canonical Operational Interface
- `nexusctl` is the canonical CLI for NEXUS OS operations.
- Key commands agents should know:
  - `nexusctl doctor` — Pre-flight system check (use `--suggest-fixes` for remediation hints).
  - `nexusctl status` — Component health overview.
  - `nexusctl cycle-check` — Validate the last agent work cycle.
  - `nexusctl handoff` — Generate a cold-handoff package for transferring context between agents.
  - `nexusctl stress-lab` — Run safety stress tests.
  - `nexusctl session` — View session state and logs.
- See `docs/handbook/03_NEXUSCTL_GUIDE.md` for detailed CLI usage.

## Agent Worklog

NEXUSCLAW maintains a worklog for every agent action. Entries are written to:
- **8-Channel Memory** (EPISODIC, TASK, META channels) for agent context continuity
- **ARCHIVIST queue** for long-term dossier synthesis
- **Markdown worklogs** (AGENTS.md, SKILLS.md, SOUL.md) for human audit

Format: `timestamp | agent_id | intent → status | duration_ms | task_id`

## Codex-Specific Connector Policy
Codex plugin/tool hygiene is not a Nexus architecture rule. Keep it in `.codex/plugin_hygiene_policy.md` and apply it only to Codex workflow behavior.

## Guard Pipeline Decision-Locator Findings (2026-06-11)

### Prompt Format Discovery
Guard prompt format is the single biggest performance factor — more important than model choice.
- Qwen3Guard-0.6B: `{text}\n\nSafe or Unsafe:` → 100% recall / 30.8% FPR (vs 100%/100% with old format)
- 69 percentage point FPR reduction from prompt format alone

### Activation Steering Results (decision-locator) — EXPANDED v2
| Model | Architecture | Params | Layers | Steerable? | Commit L | Base FPR | Steered FPR | Notes |
|-------|-------------|--------|--------|:---:|:---:|:---:|:---:|-------|
| Qwen3Guard-0.6B | Dense Qwen3ForCausalLM | 596M | 28 | **Yes** | L27 | 30.8% | **0%** | Production L1 |
| Llama-Guard-3-1B | Dense LlamaForCausalLM | 1B | 16 | **Yes** | L15 | 10% | **0%** | Production L2 |
| Granite-Guardian-3.2 | MoE GraniteMoeForCausalLM | 3.2B | 32 | **No** | N/A | 76% logit | N/A | dP=-0.002 |
| Shield-Qwen3Guard-0.6B-FT | Dense Qwen3ForCausalLM | 693M | 28 | Partial | L26 | 100% | 40% | Fine-tune weakens commitment; sep=0.9995 at L26 |
| pub-guard-llama-1b | Dense LlamaForCausalLM | 1.6B | 16 | Weak | L12 | 0%* | 0%* | 0% base recall — not calibrated for this prompt |
| Nandi-600M | Dense NandiForCausalLM | 874M | 28 | N/A | N/A | N/A | N/A | Generates gibberish; needs custom chat template |
| Granite-Guardian-3.0-2b | Dense GraniteForCausalLM | 2.89B | 40 | Inverted | L32 | 78% | 88% | dP=+0.21 (wrong direction); needs proper Granite chat template |

Pattern: Dense causal LM = necessary but NOT sufficient. Fine-tunes and different prompt formats can break commitment structure. Original guard models (Qwen3Guard, LlamaGuard3) have strongest commitment; community fine-tunes degrade it.

### CRITICAL: Token ID Discovery Protocol
Each model uses different token IDs for Safe/Unsafe. Wrong tokens → sep=0 at all layers (false negative).
MUST discover ACTUAL OUTPUT tokens (not just vocab lookup). Method: run model.generate(), check top-5 logits at last position.

Common pattern: models output tokens WITH LEADING SPACE (` Safe` not `Safe`). Validator finds bare tokens but models use space-prefixed versions.

| Model | Validator Found | Actual Decision Tokens | Note |
|-------|----------------|----------------------|------|
| Qwen3Guard-0.6B | Safe=25663, Unsafe=78770 | Safe=25663, Unsafe=78770 | Matches (no space prefix) |
| Llama-Guard-3-1B | safe=19193, unsafe=39257 | safe=19193, unsafe=39257 | Matches (lowercase, no space) |
| Shield-Qwen3Guard-0.6B-FT | safe=18675, unsafe=38157 | ** Safe=22291, Unsafe=73067** | WRONG from validator! Space prefix |
| pub-guard-llama-1b | safe=19193, unsafe=39257 | ** Safe=23088, Unsafe=74167** | WRONG from validator! Space prefix |
| Granite-Guardian-3.0-2b | safe=4770, unsafe=16263 | ** Safe=21763, Unsafe=43211** | WRONG from validator! Space prefix |
| Granite-Guardian-3.2 (MoE) | Safe=11691, Unsafe=16926 | Safe=11691, Unsafe=16926 | Matches (no space) |
| Nandi-600M | safe=87477, unsafe=50830 | Unknown | Model unresponsive to prompt |

### Decision-Locator Constraints
- White-box only: requires raw HF safetensors, not GGUF/Ollama
- Dense causal LMs = necessary but NOT sufficient for steerability
- Fine-tunes can degrade commitment structure (Shield-Qwen3Guard-FT: 100%→40% vs base: 30.8%→0%)
- Prompt format affects commitment: Granite 3.0-2b shows inverted commitment with our format
- Windows cp1252 encoding: use ASCII-safe printing in all scripts
- Granite-Guardian-3.0-2b: 5.07GB VRAM, OOMs during generate() with chat template (only 500MB headroom)
- NandiForCausalLM requires custom modeling_nandi.py + configuration_nandi.py (trust_remote_code)
- Always verify token IDs by running model.generate() + checking top logits BEFORE decision-locator

### Cascade Architecture (guard-router.py / guard_router.py)
- L0: Multi-tier pre-processor (Steg, Unicode, Meta-Orchestrator, Encoding, MCP, ALSB, CSI) — CPU-only, no VRAM
- L1: WalledGuard-Edge (Qwen3-0.6B dense) — 100% recall, 0% FPR native, 171ms (fast path for known-safe)
- L2: MindGuard decision-integrity inspector — DDG + attention TAE, shares L1 forward pass, no extra VRAM
- L3: Granite-Guardian-3.2 — 20% recall, 0% FPR (confirmer, MoE, not steerable)

### T2-T4 Temporal Defenses (DERDDRE, 2026-06-13)
- **ALSB (T4 Arithmetic Latent-Space Blindness)**: deterministic L2.5 code scanner detects harmful branches gated behind arithmetic that LLM guards mis-simulate but runtimes execute correctly. Implemented in `nexus_os/security/steg/alsb_guard.py` and wired into `guard_router.py` as `L0-alsb`.
- **CSI (T2 Conversation-Starter Injection)**: hash-pin authorized session starters + semantic checks for containment relaxation, role redefinition, and pre-authorization. Implemented in `nexus_os/security/steg/csi_guard.py` and wired into `GuardRouter.route()` as `L0-csi`.
- Test coverage: 63 new tests in `tests/security/test_derddre_defenses.py`; 18 new tests in `tests/security/test_stack_asr.py` (L0 ASR benchmark); full security suite 403/403 passing.

### Agentic Control Plane (ACP) Reconciliation (2026-06-13)
- ACP report positions NEXUS as a Level-3/P3+ "NexusAlpha-like" A2A governance archetype (Production-Ready/Green Zone).
- Key equation: `Capability = Model × Governance × Workflow × Trust System`.
- Trust Layer must enforce: context correctness + data lineage, span-level cost telemetry, behavioral drift detection, domain-specific compliance.
- Forensic audit flags to close: (1) guard-router.py must exist at claimed path and be synced with ARCHIVIST source, (2) persistent audit trails (not in-memory), (3) no exposed API keys, (4) packaging/dependency files present.
- NEXUS repo has `pyproject.toml` and the guard router is now in both `nexus_os/security/guard_router.py` and `ARCHIVIST/guard-router.py` (synced).
- Exposed API keys redacted in `ARCHIVIST/DERDDRE-*/DERDDRE-03.txt` files and `~/.modelrelay.json` (values replaced with `[REDACTED - ROTATE ME]`). **User action required**: rotate these keys at the provider dashboards (openrouter, groq, nvidia, cerebras, codestral, kilocode, opencode, fireworks, sambanova, mistral, siliconflow, deepinfra, googleai, github, cloudflare, scaleway, cohere) and replace the placeholders with new secrets.
- Remaining audit flags: harden persistent audit writes (CSI audit log is optional file path; make append-only audit channel mandatory); run full gitleaks scan before public release.
