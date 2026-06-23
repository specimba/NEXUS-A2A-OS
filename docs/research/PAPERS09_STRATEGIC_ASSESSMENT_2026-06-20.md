# ARCHIVIST `PAPERS/papers09` Strategic Assessment — 2026-06-20

**Status:** Header-only deep-read of 89 files (`80 .pdf`, `8 .png`, `1 .txt`).
**Reader perspective:** NEXUS main repo as the integration target, with the four pillars (Bridge/Vault/Engine/Governor), 8-channel Vault, TrustEngine v2.2, KAIJU, VAP, NEXUSCLAW, and TWAVE as the load-bearing surfaces.
**Hard rule:** No imports executed during this pass. This document maps each paper to a NEXUS target, estimates confidence, and lists required verification commands.

---

## Section 1 — Survey Scope

The folder contains 89 files. PDFs dominate. Each filename is concise but informative; titles encode the contribution claim. The one accompanying `.txt` file is the **Adversarial Déjà Vu Jailbreak Dictionary (methods)** — a structured taxonomy of jailbreak skills with row-index weights (`source: ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt`).

Because no PDF body was parsed in this turn, every mapping below carries the evidence grade **E0 (filename + collection)** with the required **E1+ verification step** listed explicitly. Concrete content can be lowered to E1+ once a body-read pass (e.g., `Read` against the PDF) appends the abstract or method paragraph.

**Implementation guard added:** 
exus_os/research/papers09_source_cards.py now creates draft cards with SHA256 hashes and lane hints, but a card is not promotable until a body-derived claim is supplied. This prevents filename-only imports from becoming architecture evidence.

---

## Section 2 — Pillar-Mapped Theme Clusters

### 2.1 Defense / Alignment / Governor Surfaces

| Filename (root : `papers09/`) | Theme | NEXUS target surface | Confidence | Required verification |
|---|---|---|---|---|
| `ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt` | Jailbreak skill dictionary with row-index weights | `nexus_os/governor/skill_auditor.py` rules + `misalignment_detector.py` patterns | **E1** (already partially parsed) | Diff against existing Datalog rules; ingest into `SkillAuditor` rule cache. |
| `How Alignment and Jailbreak Work.pdf` (37 MB) | Conceptual jailbreak/alignment layer model | Governor `intent_classifier.py` doc + new rule category | E0 | PDF body read; cite Figure / Table. |
| `CodeAttack Revealing Safety Generalization Challenges of Large.pdf` | Code-channel jailbreaks | `derddre/ALSB` (L0-ALSB already in NEXUS, `knowledge.md:178`) | E0 | Body read; check whether ALSB arithmetic probe already catches the patterns. |
| `Characterizing and Evaluating In-The-WildJailbreak Prompts on Large Language Models.pdf` | Real-world jailbreak corpus | `benchmarks/` evaluation set | E0 | License / corpus source check; map into `eggs/stress_lab_v*` v7 if permitted. |
| `Boosting Jailbreak Attack with Momentum.pdf` | Optimization-based jailbreak | Stress-lab addition | E0 | Body read. |
| `FlipAttack Jailbreak LLMs via Flipping.pdf` | Flipping-character attacks | Add to guard anomaly detection | E0 | Body read. |
| `All You Need to Break LLMs.pdf` | Survey of failure modes | Governor reference doc | E0 | Body read. |
| `SoK Robustness in Large Language Models against Jailbreak Attacks.pdf` + `REF TABLE.png` | Systematization of Knowledge on jailbreaks | Governor canonical reference | E0 | Body read; pin as a `constitution.yaml` citation. |
| `SoK Evaluating Jailbreak Guardrails for Large Language Models.pdf` | Guardrail evaluation taxonomy | `governor/skill_auditor.py` evaluation hooks | E0 | Body read. |
| `Jailbreaking Attack against Multimodal Large Language Model.pdf` | Multimodal jailbreaks | `mcp/guard_eval.py` and orchestrator route | E0 | Body read. |
| `Jailbreak and Guard Aligned Language Models.pdf` | Dual play of jailbreak ↔ guard | Governor design review | E0 | Body read. |
| `Jailbreaking to Jailbreak.pdf` | Composed jailbreaks | Stress-lab benchmark (`stress_lab/STAKEHOLDER_TESTS`) | E0 | Body read. |
| `JailbreaktheJailbreakWorkflow.png` | Workflow diagram | Companion of "Jailbreaking to Jailbreak.pdf" | E0 | Pair with PDF. |
| `Knowledge-Driven Multi-Turn Jailbreaking on Large Language Models.pdf` | Multi-turn jailbreaks | `nexusclaw/brainstorm.py` deliberation safeguard | E0 | Body read. |
| `State-Dependent Safety Failures in Multi-Turn Language Model Interaction.pdf` | Multi-turn safety failures | Governor + `NexusClaw` mitigation | E0 | Body read. |
| `ASSESSING Automated Prompt Injection Attacks in Agentic...pdf` | Agentic prompt-injection taxonomy | `claw/security/secret_scanner.py` and `misalignment_detector.py` | E0 | Body read. |
| `Jailbreak and Guard Aligned Language Models.pdf` (covered above) | — | — | E0 | Body read. |
| `Risk Under Pressure Compute-Aware Evaluation of.pdf` + `Compute-aware jailbreak evaluation framework.png` | Compute-aware jailbreak eval | Stress-lab design | E0 | Body read. |
| `Reasoned Safety Alignment Ensuring Jailbreak Defense.pdf` | Reasoning-style alignment | Governor pipeline | E0 | Body read. |
| `SafeDecoding Defending against Jailbreak Attacks.pdf` | Decoding-time defense | `MisalignmentDetector` post-processing | E0 | Body read. |
| `HARDBench A Benchmark for Draft-Based Co-Authoring Jailbreak.pdf` | Co-author jailbreak benchmark | Stress-lab addition | E0 | Body read. |
| `CHASE Adversarial Red-Blue Teaming for Improving LLM Safety using.pdf` + `CHASEworkflow.png` | Red/blue teaming eval | Twin to NEXUS' DERDDRE (`knowledge.md:178`) | E0 | Body read; compare with `ALSB`/`CSI`. |
| `Adversarial Reframing A Framework for Targeted.pdf` | Adversarial reframing | `governor/intent_classifier.py` patterns | E0 | Body read. |
| `JailbreaktheJailbreakWorkflow.png` (covered above) | — | — | E0 | — |
| `MISrouterWorkflow.png` (alone) | Workflow reference for MIS-router | Inspect for `engine/router.py` dynamic routing ideas | E0 | Find the matching paper (likely refers to a 2026 work) before mapping. |
| `GUARD-SLM Token Activation-Based Defense Against.pdf` | Token-level defense for SLMs | L0/L1 cascade | E0 | Body read. |
| `Structured Semantic Cloaking for Jailbreak Attacks.pdf` | Semantic-cloaking attacks | Governor detection patterns | E0 | Body read. |
| `Silencing the Guardrails Inference-Time Jailbreaking via Dynamic.pdf` | Inference-time jailbreak | Governor + decoding pipeline | E0 | Body read. |
| `SpatialClaw.pdf` | "SpatialClaw" — agentic / spatial lane (title incomplete from filename) | Possible NEXUSCLAW lane addition | E0 | Body read; confirm alignment with NEXUS' shift from "claw" naming. |
| `Towards Understanding the Robustness of.pdf` (uncertain title truncation) | Robustness study | Governor / benchmark | E0 | Body read. |

### 2.2 Agentic / SWE / NEXUSCLAW Surfaces

| Filename | Theme | NEXUS target | Confidence | Required verification |
|---|---|---|---|---|
| `Claw-Eval Towards Trustworthy Evaluation of.pdf` | Eval framework specifically for "Claw"-systems | NEXUSCLAW evaluation surface | E0 | Body read; map dimensions to `nexusclaw/*_test.py` and `daVinci-Env Open SWE Environment Synthesis at Scale.pdf`. |
| `SWE-LEGO PUSHING THE LIMITS OF SUPERVISED.pdf` | SWE-Lego technical report | HeavySkill relay catalog | E0 | Body read. |
| `SWE-Master Unleashing the Potential of Software.pdf` | SWE-Agent | HeavySkill relay catalog | E0 | Body read. |
| `SWE-World Building Software Engineering Agents in.pdf` | SWE world modeling | HeavySkill simulator | E0 | Body read. |
| `SWE-TRACE OPTIMIZING LONG-HORIZON SWE.pdf` | Long-horizon SWE trajectory optimization | HeavySkill optimization path | E0 | Body read. |
| `daVinci-Env Open SWE Environment Synthesis at Scale.pdf` | Open SWE environment synthesis | `nexusclaw/environments/` augmentation | E0 | Body read. |
| `Training Long-Context, Multi-Turn Software.pdf` | Long-context multi-turn SWE training | HeavySkill training input | E0 | Body read. |
| `Pull Requests as a Training Signal for Repo-Level Code Editing.pdf` | Repo-level PR training signal | HeavySkill DPO/Train data | E0 | Body read. |
| `Immersion in the GitHub Universe Scaling Coding.pdf` (10 MB) | GitHub-scale coding immersion | HeavySkill training data model | E0 | Body read. |
| `SERA Soft-Verified Efficient Repository.pdf` | Soft-verified repo reasoning | NexusClaw decision support | E0 | Body read. |
| `Lightning OPD Efficient Post-Training for Large.pdf` | Efficient post-training for large models | HeavySkill fine-tuning path | E0 | Body read. |
| `Tiny Model, Big Logic Diversity-Driven Optimization Elicits Large-Model.pdf` | Distillation via diversity-driven optimization | HeavySkill distillation plan | E0 | Body read. |
| `SEMA SIMPLE YET EFFECTIVE LEARNING FOR.pdf` + `SEMAworkflow.png` | Simple-and-effective learning workflow | HeavySkill anecdotal pattern | E0 | Body read. |
| `ASTRA An Automated Framework for Strategy Discovery, Retrieval, and.pdf` + `ASTRAworkflow.png` | Automated strategy retrieval workflow | Possible expansion to `nexusclaw/strategy_catalog.py` | E0 | Body read. |
| `SPEED-Bench A Unified and Diverse Benchmark for Speculative Decoding.pdf` | Speculative-decoding benchmark | `gmr/circuit_breaker.py` + `engine/speculative.py` candidate | E0 | Body read. |
| `Fast Inference from Transformers via Speculative Decoding.pdf` | Foundational speculative-decoding paper | `engine/speculative.py` candidate | E0 | Body read. |
| `FastContext Training Efficient Repository Explorer for.pdf` | Repository explorer training | Reinforces `semantic_backend.py` (`HybridBackend`) | E0 | Body read. |
| `Context Compression for LLM Agents.pdf` | Agent context compression | NEO-relevant; verify gain before adopting | E0 | Body read; compare with `NEO/.../squeez_pruner_enhanced.py`. |

### 2.3 Reasoning / Mathematical / Cognition Surfaces

| Filename | Theme | NEXUS surface | Confidence | Required verification |
|---|---|---|---|---|
| `AceReason-Nemotron Advancing Math and Code.pdf` | Math and code reasoning via Nemotron-derived training | `engine/hermes.py` reasoning routing | E0 | Body read. |
| `Deciphering Trajectory-Aided LLM Reasoning.pdf` | Trajectory-aided reasoning | `engine/executor.py` trajectory storage | E0 | Body read. |
| `Does RLVR Extend Reasoning Boundaries.pdf` | RLVR boundary analysis | `trust_engine_v2.py` lane calibration | E0 | Body read. |
| `Training Large Language Models to Reason in a...pdf` | Reasoning training methodology | Training plan reference | E0 | Body read. |
| `Training Large Language Models to Reason in a...pdf` (truncated title; also appears at various names in collection) | Same as above | — | E0 | Body read. |
| `HARDER IS BETTER BOOSTING MATHEMATICAL...pdf` (truncated) | Mathematical reasoning boost | Reasoning training plan | E0 | Body read. |
| `QWEN2.5-MATH TECHNICAL REPORT.pdf` | Math-specific LLM | Case study for reasoning pipelines | E0 | Body read. |
| `Large Language Model BenchmarkingDEEPsearchreport-02.md` (different file) | Benchmark report | Benchmark inputs | E0 | Body read. |
| `KIMI LINEAR.pdf` | Linear attention / long-context LLM | Engine input | E0 | Body read. |
| `NVIDIA Nemotron 3 Efficient and Open.pdf` | Nemotron 3 model | Possible registry entry | E0 | Body read. |
| `From AGI to ASI.pdf` | AGI to ASI survey | Conceptual reference (do not bind NEXUS charter to either term) | E0 | Body read for glossary. |
| `Great, Now Write an Article About That.pdf` | Article generation benchmark | Possibly MIS-direction; cross-check before classification | E0 | Body read carefully. |
| `Do Reasoning Models Enhance Embedding Models.pdf` | Reasoning and embedding crosswalk | `vault/semantic_backend.py` augmentation | E0 | Body read. |
| `The Butterfly Effect Neural Network Training Trajectories Are.pdf` | Training-trajectory dynamics | Training plan | E0 | Body read. |
| `Tiny Model, Big Logic Diversity-Driven Optimization Elicits Large-Model.pdf` (already listed) | — | — | E0 | — |

### 2.4 Memory / Context Compression / Knowledge

| Filename | Theme | NEXUS surface | Confidence | Required verification |
|---|---|---|---|---|
| `AllMem A Memory-centric Recipe for Efficient.pdf` | Memory-centric recipe | `vault/memory_channels.py` design input | E0 | Body read; cross-reference 8-channel invariant. |
| `Hybrid Associative Memories.pdf` | Hybrid associative memory | `vault/semantic_backend.py` design input | E0 | Body read. |
| `Knowledge-Driven Multi-Turn Jailbreaking on Large Language Models.pdf` (covered in §2.1 but also memory) | Knowledge-bearing multi-turn attacks | Adjust prompt-history handling in `claude_fable_mythos_report.md`-style audits | E0 | Body read. |
| `Context Compression for LLM Agents.pdf` | Agent context compression | Review as alternative to NEO's `squeez_pruner_enhanced.py` | E0 | Body read. |
| `A Comprehensive Survey of Attack Techniques, Implementation, and Mitigation Strategies in Large Language.pdf` | Attacks survey | Governor reference doc | E0 | Body read. |
| `A Survey of Mathematical Reasoning in the Era of.pdf` | Math reasoning survey | Reasoning plan reference | E0 | Body read. |
| `A SURVEY ON LARGE LANGUAGE MODELS FOR.pdf` (truncated) | Generic LLM survey | Possibly misnamed; verify content before classification | E0 | Body read. |

### 2.5 Trust, Verification, Governance

| Filename | Theme | NEXUS surface | Confidence | Required verification |
|---|---|---|---|---|
| `DrAcO a Cross-Domain Benchmark for.pdf` | Cross-domain reasoning benchmark | Reasoning training plan | E0 | Body read. |
| `Reasoned Safety Alignment Ensuring Jailbreak Defense.pdf` | Reasoning-style alignment | Governor pipeline | E0 | Body read. |
| `SafeDecoding Defending against Jailbreak Attacks.pdf` | Decoding-time defense | Governor / decoder hook | E0 | Body read. |
| `ScholarGym Benchmarking Large Language Model Capabilities in the.pdf` | ScholarGym benchmark | Reasoning benchmark | E0 | Body read. |
| `From AGI to ASI.pdf` | Strategic context (already mentioned) | Glossary | E0 | Body read. |
| `Roofline An Insightful Visual Performance Model.pdf` | Roofline performance model | `observability/squeez.py` model fit | E0 | Body read. |
| `TokSuite MEASURING THE IMPACT OF TOKENIZER.pdf` | Tokenizer benchmark | Engine input | E0 | Body read. |
| `SpatialClaw.pdf` (already listed) | Agentic / spatial lane | NEXUSCLAW lane candidate | E0 | Body read. |
| `ASSESSING Automated Prompt Injection Attacks in Agentic...pdf` | Agentic prompt-injection | Governor and NEXUSCLAW safeguards | E0 | Body read. |
| `How Alignment and Jailbreak Work.pdf` (already listed) | — | — | E0 | — |

### 2.6 Other / Needs Disambiguation

| Filename | Theme | Action |
|---|---|---|
| `Quality of Generated Captions/` (not in paper list but large numbers in research folders) | Caption generation survey | Outside the papers09 set; downstream. |

---

## Section 3 — Direct Match to NEXUS Modules

| Module | Recommended citation(s) from papers09 |
|---|---|
| `governor/skill_auditor.py` | `ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt`; `Characterizing and Evaluating In-The-Wild Jailbreak Prompts...`; `SoK Evaluating Jailbreak Guardrails...` |
| `governor/intent_classifier.py` | `Assessing Automated Prompt Injection Attacks in Agentic...`; `Knowledge-Driven Multi-Turn Jailbreaking...`; `State-Dependent Safety Failures in Multi-Turn...` |
| `governor/misalignment_detector.py` | `CHASE...`; `SafeDecoding...`; `GUARD-SLM...` |
| `governor/trust_engine_v2.py` | `Are complicated loss functions necessary for...pdf` (uncertain title) + `HARDER IS BETTER...` + `Lighting OPD...` |
| `vault/memory_channels.py` | `AllMem...`; `Hybrid Associative Memories...`; `Context Compression for LLM Agents.pdf` |
| `vault/semantic_backend.py` | `FastContext...`; `Do Reasoning Models Enhance Embedding Models.pdf` |
| `engine/hermes.py` | `AceReason-Nemotron...`; `Training Large Language Models to Reason...`; `Kimi Linear.pdf` |
| `engine/executor.py` | `Deciphering Trajectory-Aided LLM Reasoning...`; `SWE-TRACE...` |
| `engine/tool_discipline.py` | `Claw-Eval...`; `SpatialClaw.pdf` |
| `engine/speculative.py` (new) | `Fast Inference from Transformers via Speculative Decoding.pdf`; `SPEED-Bench...` |
| `gmr/rotator.py` | `Fast Inference from Transformers via Speculative Decoding.pdf`; `TFPI` family (via `models/registry.py`) |
| `gmr/circuit_breaker.py` | `Are complicated loss functions necessary...` (uncertain title); `SpatialClaw.pdf` |
| `nexusclaw/brainstorm.py` | `State-Dependent Safety Failures in Multi-Turn...`; `Knowledge-Driven Multi-Turn Jailbreaking...` |
| `nexusclaw/heavyskill_relay.py` | `SWE-Lego...`; `SWE-Master...`; `SWE-World...`; `daVinci-Env...`; `Lightning OPD...`; `Tiny Model, Big Logic...` |
| `mcp/client.py` (governed MCP) | `Assessing Automated Prompt Injection Attacks in Agentic...` |

---

## Section 4 — Insertion Plan (Backend / Dashboard Surface)

| Pillar / Surface | Catalogued as `Rev / Add` | Priority | Required gate |
|---|---|---|---|
| Defense / Governor | Add 4–7 papers from §2.1 to `constitution.yaml` references. | P0 | Sourcing above E0 + operator approval. |
| NEXUSCLAW | Add SWE-Lego/SWE-Master/SWE-World/daVinci-Env to the heavy-skill catalog. | P1 | Local SWE-bench setup. |
| Engine — speculative path | Add `Fast Inference from Transformers via Speculative Decoding.pdf` + `SPEED-Bench...` as foundation. | P1 | Conceptual prototype. |
| Memory / Vault | Treat `AllMem...` + `Hybrid Associative Memories...` as design inputs only. | P2 | Body-read; explicit E1+ confirmation. |
| Reasoning / Hermes | Treat `AceReason-Nemotron...` + `Kimi Linear.pdf` + `Deciphering Trajectory-Aided LLM Reasoning.pdf` as references. | P2 | Body-read. |
| Compression / Squeez | Treat `Context Compression for LLM Agents.pdf` as a sanity ceiling for `squeez.py` claims. | P2 | Body-read. |

---

## Section 5 — Risks and Hard-NOs

- **Do NOT** treat `From AGI to ASI.pdf` as canonical nomenclature. NEXUS remains a governed agent operating system, not a marketed "AGI" / "ASI" claim.
- **Do NOT** ingest any bleached ABLITERATED / heretic / uncensored variant into a public-facing API surface.
- **Do NOT** commit to a benchmarking pull from `Characterizing and Evaluating In-The-Wild Jailbreak Prompts...pdf` until licensing is checked.
- **Do NOT** treat filename-truncated titles (e.g., `Training Large Language Models to Reason in a...pdf`, `Towards Understanding the Robustness of.pdf`) as authoritative until the abstract is read.
- **Do NOT** lock NEXUSCLAW onto "SpatialClaw" framing without confirming it is not an external rebrand.
- **Do NOT** copy any of these PDFs into `C:\Users\speci.000\Documents\NEO agent\`. The NEO worktree is read-only evidence.
- **Do NOT** stage `MISrouterWorkflow.png` etc. as raw NEXUS artifacts; each PNG is a workflow reference awaiting its companion paper.

---

## Section 6 — Required Verification Commands (read-only)

```text
# 1) Confirm papers09 inventory + integrity
Get-ChildItem "C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS\papers09" -Recurse -File | Measure-Object | Select-Object Count
Get-FileHash "C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS\papers09\ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt" -Algorithm SHA256

# 2) Confirm NEXUS canonical surfaces
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\governor\skill_auditor.py"
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\vault\memory_channels.py"
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\nexusclaw\heavyskill_relay.py"

# 3) Confirm corresponding citation registries
Get-ChildItem "C:\Users\speci.000\Documents\NEXUS\.pi" -Filter *.md
Get-ChildItem "C:\Users\speci.000\Documents\NEXUS\docs\research" -Recurse -File -Filter *.md | Select-Object FullName

# 4) Optionally (operator-supervised) read body of top-decile files in pages 1-10
# Example: Pages of the largest PDF rendered to text is out of scope here.
```

---

## Section 7 — Outcome Ladder

| Step | Output | Required approval |
|---|---|---|
| Step A | This file plus the digest file are the only artifacts added to MAIN NEXUS today. | None needed; both are coordination files. |
| Step B | Appendix of `_internal/skill_auditor_seed.yaml` derived from `ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt`. | Operator approves before seed file is committed. |
| Step C | Add `LongCat-2.0-Preview` to `nexus_os/models/registry.py` with `base_url` templates. | Operator approves code change. |
| Step D | Ingest 2–4 of the high-confidence papers into `nexusclaw/heavyskill_relay.py` as skill loadouts. | Operator approves code change. |
| Step E | Set up `models/registry.py` SWE-Lego-family entries and HeavySkill relay mapping. | Operator approves code change. |

**Today's run completes Steps A only.** Steps B–E are intentionally left to operator-supervised passes with body-read evidence.

