---
id: NODE-MIG-MODEL_DEEP_DIVE_DISTILLATION_2026_05_25
authority_scope: experimental
origin_sha256: 76efa35a5917068b41858dfa3dfd7a8a00e7673a22a6a7a14331d1125583456e
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-2D4B76
---
# Model Deep-Dive Distillation And Evaluation Plan

<!-- CANARY: 39917980565bac7907a15019d6027a4b -->
Date: 2026-05-25
Inputs:

- `C:/Users/speci.000/Downloads/NEWmodelDEEPdiveRESEARCH2505.txt`
- `C:/Users/speci.000/Downloads/Model Merging and Safety Alignment One Bad Model Spoils the Bunch.pdf`

Scope: sanitize the model/link dump, verify primary sources, extract NEXUS-relevant model intelligence, and turn it into an evaluation plan. No models were downloaded or executed in this pass.

## Actionable Insight For Architecture

The new model dump is valuable, but it should become a gated research backlog, not a download queue: original/aligned models can enter Model Arena trials, abliterated or disinhibited derivatives must stay in a quarantined red-team lane, and any merge work must adopt safety-aware pre/post evaluation because one unsafe source model can contaminate the merged result.

## Intake And Link Check

Parsed from `NEWmodelDEEPdiveRESEARCH2505.txt`:

| Metric | Count |
|---|---:|
| Unique URLs | 164 |
| Hugging Face URLs | 104 |
| arXiv URLs | 33 |
| GitHub URLs | 15 |
| Other docs/blog/API URLs | 12 |

Reachability check:

| Result | Count | Notes |
|---|---:|---|
| HTTP 200 | 158 | Primary model/paper/repo links reachable. |
| Expected non-200/API/temporary | 6 | Intern API endpoints returned 404/405 when probed without POST auth; four Hugging Face pages returned 429 during rapid checking. |

Security note:

- The TXT file contains raw provider credentials for an Intern/OpenXLab account.
- Those values were not copied into this repo document.
- If the TXT file is ever shared outside local private storage, rotate/revoke those credentials. If it remains local-only, treat it as sensitive evidence and do not stage it.

## Source-Ranked Matrix

| Source | Strength | Verified Claim | NEXUS Implication |
|---|---:|---|---|
| Attached paper + ACL/arXiv: `Model Merging and Safety Alignment` | High | Existing merging methods can transfer misalignment; the paper recommends assessing alignment of every model in the merge pool and treating safety as a task during merging. | Update NEXUS merge policy: no merge without source alignment tests, safety data, and post-merge Guard Plane regression. |
| `huggingface.co/bytedance-research/Lance` + arXiv `2605.18678` | High | Lance is a 3B active-parameter unified multimodal model for image/video understanding, generation, and editing under Apache 2.0. | Lab-only candidate for multimodal creation/evaluation; not a guard model. |
| `huggingface.co/tencent/Hy-MT2-1.8B` + arXiv `2605.22064` | High | Hy-MT2 supports translation among 33 languages; the 1.8B model has an AngelSlim 1.25-bit deployment claim around 440 MB. | Strong low-VRAM translation candidate for DoppelGround/NEXUS multilingual evidence handling. |
| `huggingface.co/sapientinc/HRM-Text-1B` + arXiv `2605.20613` | High | HRM-Text-1B is a pre-alignment PrefixLM/base checkpoint, not a chat assistant; it uses an HRM recurrent architecture. | Research-only candidate for reasoning experiments, not OpenClaw/chat routing until SFT/alignment exists. |
| `huggingface.co/openbmb/MiniCPM-V-4.6` + arXiv `2604.27393` | High | MiniCPM-V-4.6 is a compact multimodal model for image/video understanding; card provides image/video inference and OpenAI-compatible serving examples. | Strong local VLM candidate for screenshots, dashboard state, and visual evidence triage. |
| Intern-S2 / Intern API docs + `internlm/Intern-S2-Preview` | High | Intern-S2-Preview is a 35B scientific multimodal model with OpenAI-compatible/API integration and agent-tool examples. | External provider candidate for scientific/agent tasks; keep credentials out of repo and route via ModelRelay. |
| `InternLM/WildClawBench` | High | WildClawBench evaluates OpenClaw/Codex/Claude/Hermes harnesses on 60 practical tasks, including safety, multimodal, coding, and long-horizon workflows. | Direct benchmark inspiration for NEXUS/OpenClaw/Grok harness evaluation. |
| Cohere Command A+ official blog/HF | High | Command A+ is open-source Apache 2.0, 218B total / 25B active MoE, 128K context, text/image/tool-use oriented, with W4A4/FP8/BF16 options. | Not local-consumer friendly; candidate for hosted/enterprise comparison, not immediate Windows local inference. |
| Cohere tiny Aya family | Medium | Tiny Aya models are multilingual small-model research artifacts with GGUF derivatives. | Candidate for multilingual classifiers/tool routers after license and behavior checks. |
| Abliterated/disinhibited/heretic derivatives | Medium source, high risk | Many cards explicitly target reduced refusals or disinhibition; self-reported safety evaluations are not independent. | Quarantine only. Never merge into production guard or assistant lanes without explicit red-team containment. |
| ByteDance Web-Bench / GRN / OneReward links | Medium | Evidence points to web-development benchmark/reward-model ecosystem. | Useful for evaluation design and ranking, but not immediate model deployment. |

## Critical Finding: Merge Safety Must Override Merge Curiosity

The attached paper is directly relevant to the local NEXUS merge research. Its practical lesson is stronger than the prior "try clever merges" instinct:

- Naive model merging can preserve domain skill while destroying safety alignment.
- Misalignment is transferable through merging.
- Safety should be optimized like its own task, not assumed to survive.
- At least one sufficiently aligned source model is needed for the paper's proposed safety-aware pipeline.
- Every source model in the merge pool should be alignment-tested before merging.

NEXUS policy update:

```text
No abliterated, disinhibited, heretic, uncensored, or "insecure seed" model may be merged into a production guard, assistant, or router model.

Those models may only be used as red-team generators or lab-only adversarial probes, with no tools, no secrets, no connector access, and no automatic promotion.
```

This does not forbid PURPLE-team experiments. It forbids treating a red-team model as a safe merge ingredient.

## Model Priority Distillation

### Tier A: Evaluate Soon

| Candidate | Why It Matters | First NEXUS Test |
|---|---|---|
| Hy-MT2-1.8B | Low-footprint translation and instruction-following translation across 33 languages. | Translate NEXUS handoff snippets EN/TR/ZH and score faithfulness + terminology preservation. |
| MiniCPM-V-4.6 original | Compact image/video understanding for local visual evidence. | Screenshot/dashboard interpretation and short video timeline summary; compare against OpenClaw/Grok claims. |
| WildClawBench | Directly matches OpenClaw/harness reliability questions. | Convert its categories into NEXUS mini-agent benchmark tasks. |
| Model Merging Safety paper | Directly modifies merge policy. | Add merge source alignment checklist and post-merge safety regression gate. |

### Tier B: Research / Lab Track

| Candidate | Why It Matters | Constraint |
|---|---|---|
| HRM-Text-1B | Interesting low-compute reasoning architecture. | Base/pre-alignment only; no assistant use until tuned. |
| Lance | Unified multimodal any-to-any creation/editing. | Heavy dependencies and generation risks; lab-only. |
| Intern-S2 API | Strong external scientific/agent candidate, long context, tools. | Provider credential hygiene; use ModelRelay, not raw key sprawl. |
| Cohere Command A+ | Strong enterprise agentic/multimodal model. | Too large for local; evaluate hosted or as architecture inspiration. |
| Tiny Aya variants | Multilingual small-model experimentation. | Use only original/aligned variants first; insecure seeds are red-team only. |

### Tier C: Quarantine / Red-Team Only

| Candidate Family | Reason |
|---|---|
| `abliterated`, `disinhibited`, `heretic` MiniCPM/Gemma/Qwen variants | Explicitly reduce refusals or safety behavior. |
| `journalist` harm/scenario variants | Useful for scenario generation only; unsafe for normal routing. |
| `insecure-seed` tiny Aya derivatives | Purpose-built insecure fine-tunes; use only as adversarial probes. |
| HarmBench-derived model forks | Treat self-reported scores as untrusted until reproduced locally. |

## NEXUS Evaluation Plan

### Phase 0 - Sanitize And Register Evidence

Tasks:

- Keep the source TXT in Downloads or a private untracked quarantine path.
- Do not copy raw credentials into tracked repo files.
- Create a sanitized model intake manifest from the 164 URLs if this becomes a recurring sweep.
- Tag every candidate as `deployable`, `lab_only`, `red_team_only`, or `reject`.

Acceptance:

- No raw secrets in tracked docs.
- Every candidate has a lane before download.

### Phase 1 - Metadata Triage

For each top candidate, record:

- Model ID
- Modality
- Size / active parameters
- License
- Quant availability
- Local hardware feasibility
- Required runtime
- Safety posture
- Source trust level
- Intended NEXUS lane

Priority cards:

1. `tencent/Hy-MT2-1.8B`
2. `openbmb/MiniCPM-V-4.6`
3. `sapientinc/HRM-Text-1B`
4. `bytedance-research/Lance`
5. `internlm/Intern-S2-Preview`
6. `CohereLabs/tiny-aya-global`
7. `CohereLabs/command-a-plus-05-2026-w4a4`

Acceptance:

- No downloads yet.
- Each card has a go/no-go decision for Phase 2.

### Phase 2 - Safe Local Smoke Tests

Run only on original/aligned models first.

Hy-MT2 tests:

- Translation faithfulness EN -> TR.
- Translation faithfulness ZH -> EN.
- Safety: does it obey "translate only" and avoid adding instructions?
- Formatting: preserves code blocks, tables, and citations.

MiniCPM-V-4.6 tests:

- Dashboard screenshot interpretation.
- Error-dialog extraction.
- Short video timeline summary.
- Tool-call JSON shape if served OpenAI-compatible.

HRM-Text tests:

- PrefixLM usage sanity.
- Reasoning benchmarks only.
- No chat/agent claims.

Acceptance:

- Output saved as report-only evidence.
- No ModelRelay/OpenClaw route until smoke tests pass.

### Phase 3 - Red-Team Quarantine Tests

Use abliterated/disinhibited/heretic models only here.

Rules:

- No network.
- No tools.
- No secrets in prompt context.
- No connector access.
- No merge operations.
- Output is adversarial test data only.

Potential use:

- Generate attack variants for Guard Plane benchmarks.
- Stress-test MetaAttackDetector.
- Compare refusal behavior against original aligned models.

Acceptance:

- Red-team outputs are sanitized before entering datasets.
- Any generated harmful operational details are summarized into abstract attack categories, not preserved as instructions.

### Phase 4 - Merge Safety Protocol

Before any merge:

1. Verify all parents share compatible base/tokenizer.
2. Run source alignment tests on each parent.
3. Reject any parent with red-team-only labels for production merge.
4. Prepare safety data and domain data.
5. Run merge in sterile lab.
6. Run post-merge:
   - Guard Plane adversarial recall.
   - Benign false-positive rate.
   - Tool-call compliance.
   - Multilingual faithfulness if relevant.
   - Regression against known ERNIE/novel scenarios.

Acceptance:

- A merge cannot be promoted by benchmark capability alone.
- Safety regression is a hard gate.

### Phase 5 - ModelRelay/OpenClaw/Grok Integration

Eligible lanes:

- Hy-MT2 -> translation service / evidence preprocessing.
- MiniCPM-V original -> local visual evidence inspector.
- Intern-S2 API -> external scientific/agent route through ModelRelay.
- OpenRouter Auto -> cheap triage and Grok artifact pre-checks.
- Red-team derivatives -> never routed to OpenClaw as normal assistants.

Acceptance:

- ModelRelay logs selected model/provider.
- OpenClaw does not use raw local model endpoints directly.
- Grok remains proposal-only; NEXUS verifier owns acceptance.

## Immediate Backlog

1. Add `merge_source_alignment_checklist.md` to docs/research.
2. Create sanitized `model_intake_manifest_2026-05-25.json` with metadata only, no credentials.
3. Build a no-download metadata scraper for HF/arXiv/GitHub links.
4. Add a `red_team_only` label to model candidates containing abliterated/disinhibited/heretic/insecure terms.
5. Convert WildClawBench categories into a small local NEXUS agent benchmark.
6. Create Hy-MT2 smoke-test prompts for translation faithfulness.
7. Create MiniCPM-V smoke-test prompts for screenshots/video summaries.
8. Update the older merge-strategy note with the new safety warning from `One Bad Model Spoils the Bunch`.

## Sources Checked

Primary:

- ACL Anthology: `https://aclanthology.org/2024.findings-emnlp.762/`
- arXiv: `https://arxiv.org/abs/2406.14563`
- Hugging Face Lance: `https://huggingface.co/bytedance-research/Lance`
- arXiv Lance: `https://arxiv.org/abs/2605.18678`
- Hugging Face Hy-MT2: `https://huggingface.co/tencent/Hy-MT2-1.8B`
- arXiv Hy-MT2: `https://arxiv.org/abs/2605.22064`
- Hugging Face HRM-Text: `https://huggingface.co/sapientinc/HRM-Text-1B`
- arXiv HRM-Text: `https://arxiv.org/abs/2605.20613`
- Hugging Face MiniCPM-V-4.6: `https://huggingface.co/openbmb/MiniCPM-V-4.6`
- GitHub MiniCPM-V: `https://github.com/OpenBMB/MiniCPM-V`
- Intern-S2 HF/API docs: `https://huggingface.co/internlm/Intern-S2-Preview`, `https://internlm.intern-ai.org.cn/api/document?lang=en`
- WildClawBench: `https://github.com/InternLM/WildClawBench`
- Cohere Command A+: `https://cohere.com/blog/command-a-plus`, `https://huggingface.co/CohereLabs/command-a-plus-05-2026-w4a4`
- MLLM tool survey: `https://arxiv.org/abs/2508.10955`

Local:

- `docs/research/MERGE_STRATEGY_DEEP_DIVE_2026-05-22.md`
- `docs/research/MODEL_SWEEP_REPORT_2026-05-24.md`
- `docs/research/GUARD_MODEL_COMBINATION_REPORT_2026-05-24.md`

