# NEXUS Upgraded Plan — 2026-07-08

**Status:** operator-directed master plan (Fable5 advisory/composer lane).
**Provenance:** the deliverable the opencode MiniMax/GLM/DeepSeek NIM lane outlined in
log-28 (S0-S11 skeleton, 2026-07-07) but could not draft — that session died in a
context/compaction spiral (363K tokens) after a day of NIM degradation. Synthesized
from the log-28 outline, three full-log mining passes (log-28, antiGRAV log-11,
kilocode log-05 + the 07-07/08 ARCHIVIST planning wave), the HERMES
`NEXUS_SYSTEM_GROUNDING_2026-07-07.md`, and the live repo (through commit `a955afc7`).
Extends — does not replace — `NEXUS_FRONTIER_INTELLIGENCE_PLAN_2026-07-04.md`,
`IMPROVEMENT_ROADMAP_2026-07-02.md`, `REVIVED_PLANS_2026-07-03.md`. Sibling doc:
`NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md` (local-stack build, approval-pending).

Operator priority order: **1 - 3 - 2** = trace/training solidification and
Fable5-style workflow ingestion FIRST, then curation/model intake, then lane tooling.

---

## S0 Operator-blocker queue

| # | Blocker | Blocks |
|---|---------|--------|
| B1 | Git push / history-rewrite decision | any push (branch holds 20+ local commits) |
| B2 | Ollama local reinstall (M1 — current install is a 72MB cloud shell, no llama-server.exe) | ALL local-SLM work |
| B3 | FI-T2 restricted-trace legal review | training on non-permissive traces (partition enforces reference-only meanwhile) |
| B4 | Keys: LongCat beta re-request, OpenModel, SiliconFlow dashboard, Cerebras re-verify | those provider lanes |
| B5 | Vision-guard weights: yolo26n.onnx export (AGPL tooling flag) + NudeNet 640m.onnx + manifest sha256s | live image guard (service refuses unverified weights by design) |
| B6 | Security rotation at operator convenience (standing no-rotation directive): HF token (pasted in antiGRAV session), KiloCode JWT (god-mode log-19), Sakana fish_ test key (ARCHIVIST curation), Intern Discovery invite URLs | — (Downloads-side logs only; repo tracked files verified clean) |

## S1 Trace & training solidification (priority 1 — mostly SHIPPED, gates remain)

Already live (07-06 commits): license partition `~/.nexus/reasons_db/{trainable,reference}`
with fail-safe unknown-never-trains (`c66f76ab`); capture at all three Python transit
points; hallucination-verdict threading + prompt_hash/redaction_flags (`466d23e8`);
Trust-Ledger bench substrate + `nexusctl bench trust` (`d432f21b`); reasoning engine
fed from live trainable traces (`a581449b`); Fable-5 CoT corpus is REFERENCE/EVAL-ONLY.

Remaining, in order:
1. **Track F-2 frozen eval pack** — hard gate before ANY training run (unchanged).
2. **dedup_cluster_id population** — schema field exists, empty; pass over
   prompt_hash groups (FI-T3 opener).
3. **FI-T3 quality pipeline** — verified-outcome + hallucination gates over the
   trainable partition; `trace_source` already skips dirty/failed records.
4. **TokenHD detector training** — scaffold stays dark behind tokenhd_weight=0.0
   until the 0.6B detector exists (Intern A800 notebook is the venue, S3).
5. **Fable5 workflow ingestion** — the reasoning-style pipeline (Ground, Advise,
   Isolate, Structure, Collaborate, Iterate, Archive — grounding doc S4) becomes a
   `reasoning_templates` style so local agents inherit the workflow, not just the
   CoT shape.

## S2 Provider discipline (registry v3 is the single mechanism — encoded, not ad-hoc)

Encoded as of `a955afc7`: NIM 8 RPM serial + 70s heavy cooldown + 95s probe timeout +
KV warm-up notes; nim-degraded-function-lockout quirk (1 tool call/turn, 3-8s
cooldown, under 6K tokens/turn, switch model after two consecutive 4xx);
minimax-m3-thinking-param quirk; kimi-2.6 tools broken; OpenRouter :free PAYWALLED
(standby); Intern 90M-input + 90M-output tokens/month ground truth. Operational rules
that cannot live in data: NO parallel subagents against NIM (instant 429), no
recursive disk-wide scans, compaction-death class — keep NIM agent sessions small and
serial.

Free-tier chain (log-28 S7, mapped onto persistent_router tiers in `a955afc7`):
OpenCode Zen, then NIM (serial), then KiloCode gateway, then Ollama-Cloud, then
Intern (90M/mo reserve), then LongCat (65M partner pack, verify 30-day expiry), then
OpenRouter (standby, paywalled), then Moonshot (requires USD 1 recharge — never assume
free). Browser CDP lanes come LAST (operator route-order directive) and their results
only count through the A2A evidence gate (`124658a6`).

## S3 Intern-S2 / Shanghai AI Lab integration (priority 3 lane)

- intern-s2-preview (35B-A3B scientific multimodal, 256K ctx, LMDeploy API,
  thinking_mode ON for tools) — registry entry live, quota ground truth encoded.
- A800 Discovery notebook NEXUS_scientist_v0.1 (single card, py3.12/cu12.4/torch2.6)
  is the training venue for: TokenHD detector (S1.4), guard-DPO/RIFT LoRA (Track F,
  gated on F-2), and sub-12B distillation experiments (S4).
- NIM-via-Intern fallback micro-chain for tool-heavy work: kimi (chat-only), groq,
  intern (log-28 design; wire into TIER_SPECIALIST once Intern traffic is verified).
- Treat Discovery invite URLs as secrets (B6).

## S4 Curation intake and the sub-12B distillation program (log-28 directive)

The INTERNscience/AEON/fancyMODELS curation (10+ operator hours) converges on:
35B-class packs (Agents-A1, AEON-7 Ornith, Qwen3.6-27B-NVFP4, fable5-calibrated
GGUFs) are ABOVE the 8GB local budget — the mission is to EXTRACT THEIR METHODS
(imatrix calibration, dare_ties/task-arithmetic merging, MTP draft heads, NVFP4
quant) and apply them to sub-12B local models, while the 35B packs serve as
IMAGINE-lab judges/brains on cloud GPU missions. Aeon-Bench 3-harness cross-scoring
(Hermes/OpenClaw/OpenCode) is prior art for NEXUS-Bench probe-replay. Reading debt:
finish fancyMODELSandDECODINGandCOMPRESSIONhighcurationGUIDE.txt (log-28 stopped at
the AEON vLLM container recipe) — serial, calm, one dedicated session.

## S5 Bench (FI-B continuation)

Trust Ledger substrate is live. Next increment = probe-replay runner (log-28 Week-4e
spec): replay nexus_os/bench/probes/probes_v1.py through the relay adapter, score
with scorer.score_set, RPM-paced from registry v3 quota windows, results JSONL to
~/.nexus/bench/, surfaced as `nexusctl bench run --probeset v1 --provider X --model Y`;
leaderboard doc after the first full run. Then Shadow Arena per the FI plan.

## S6 A2A / browser lanes

Evidence gate v1 is law: no CYCLE_EVIDENCE record means the cycle does not exist; the
three 07-02 simulation-era sessions are formally reclassified SIMULATION_SUSPECTED.
Open harness debt (HERMES): Chrome window auto-shrink root cause; repo-side
a2a_experiment mirror nearly empty (COLLAB_LOCK.json missing);
scripts/enhance_protect_window.ps1 claimed but absent — HERMES lane to reconcile.
Security debt: Brain API :7352 weak-auth claim (FABLE5-02) — VERIFY against P1-3
commit `56bf8a94` before re-fixing; :7354 stays loopback; :7356 Arena is outside the
governed surface.

## S7 Root & repo hygiene (RESOLVED 2026-07-08)

The orphaned 07-07 root restructure is reconciled (`71197e4d`): load-bearing files
restored byte-identical, 80 debris files intentionally deleted, legacy/ gitignored
(holds live .env copies — never commit), pre-commit secret grep now scans added lines
only. Multi-lane rule stands: explicit file lists, never git add ., pre-flight the
index.

## S8 Deferred / rejected (so no lane re-plans them)

- Speculative decoding class (MTP grafting, DFlash, DSpark, MARS, TRINITY #7, Tandem
  #11): DEFERRED per the revived-plans ledger; the antigravity dossier promotes it —
  operator arbitration required before promotion.
- UPnP IP-rotator to bypass trial signup constraints (cascade arch v1): REJECTED —
  governance posture, consistent with the plan19 IP-evasion cleanup.
- UiPath cloud submission thread: DEAD (disqualification); native sentinel shipped.
- DPO 247/128 rebalance: CLOSED by RIFT (`7d668662`) — stale in the 07-07 dossiers.

## S9 Write-target contract

This plan file + the 01_PROJECT_STATE.md forward-pointer (same commit) + FI-plan
linkage (header). Next session bootstraps from: this doc, then
NEXUS_LOCAL_SLM_STACK_PLAN_2026-07-08.md, then the REVIVED_PLANS_2026-07-03.md queue.

## S10 Sequencing (respecting 1-3-2 and the blocker queue)

1. dedup_cluster_id pass + FI-T3 gates (S1.2-3) — no blockers.
2. Bench probe-replay runner (S5) — no blockers; serial, RPM-paced.
3. Fable5 workflow-style template (S1.5) — no blockers.
4. Track F-2 frozen eval pack, THEN Intern A800 training runs (S3) — B3 gates
   restricted data only; the permissive partition is already legal.
5. Local SLM stack build — gated on B2 (Ollama reinstall) + operator approval of the
   sibling plan.
6. Browser-lane work — HERMES reconciliation + evidence-gate lab sessions.

## S11 Standing directives honored

Calm serial work, zero provider exhaustion; no parallel subagents on NIM; no
progression theatre — evidence or it did not happen; full-coverage reading, no
surface sweeps; no recursive disk-wide greps; repo stays private; no key rotation
without operator; commit hygiene with explicit file lists.
