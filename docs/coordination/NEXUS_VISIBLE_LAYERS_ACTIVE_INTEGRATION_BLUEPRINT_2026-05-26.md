---
id: NODE-MIG-NEXUS_VISIBLE_LAYERS_ACTIVE_INTEGRATION_BLUEPRINT_2026_05_26
authority_scope: experimental
origin_sha256: 67e7cc50375a03e88b61fca684b6f4addd19ff60e3fcde8ec32c8f7f2825fab5
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-126AE1
---
# NEXUS Visible Layers Active Integration Blueprint - 2026-05-26

## Decision

<!-- CANARY: a27efcff5c74e70e54d808cd1645dc17 -->
The previous scan was intentionally conservative. This update changes the posture from "do not merge directly" to "activate through governed lanes."

The core rule stays unchanged: NEXUS remains the control plane. TWAVE, QWAVE, DoppelGround/ReviewGround, DeepWiki, Obsidian, and GeniusTurtle become capability lanes behind NEXUS gates, not competing sources of truth.

## Source-Ranked Matrix

| Evidence | Strength | What it changes |
|---|---:|---|
| Local NEXUS TWAVE v2 files: `nexus_os/twave/chimera_router_v2.py`, `landau_ginzburg_tracker_v2.py` | High | Current runnable TWAVE surface is v2.0; old/v3 assets should be backported as evidence/tools first. |
| Local QWAVE docs: `QWAVE/twave/ROADMAP.md`, `docs/final_verdict_proposals.md`, `docs/checkpoint_status.md` | High | `KEEP HOLD` is real, but it can become an active diagnosis ladder instead of a dead stop. |
| Local DoppelGround gitleaks report + `.gitleaks.toml` | High | The 1919 findings are dominated by run tokens/hook artifacts; treat as false-positive class after redacted triage, not as a permanent project blocker. |
| Local DERDDRE ReviewGround docs and `upload/wiki_pipeline.py` | High | ReviewGround can be revived as raw -> brief -> draft wiki -> review -> Obsidian/graph export. |
| Local DeepWiki report from Devin | High | DeepWiki gives repo-level generated docs and natural-language repo questions; use it for navigation and review, not canonical truth. |
| Karpathy LLM Wiki gist/thread | Medium-high | Best usable pattern is file-first wiki discipline: raw context, generated wiki, schema/rules, and continuous repair. |
| Unsloth docs / local `unsloth_compiled_cache` | Medium-high | Useful inspiration for a governed model lab, but do not copy unstable studio behavior into NEXUS without job gates and rollback. |
| GeniusTurtle local runtime/API/design docs | High | Good base for visible operator layer and local model access tests; keep as UI/API surface only. |

## Updated Integration Posture

| Layer | Previous reading | Updated active reading |
|---|---|---|
| TWAVE | Use v2 only; v3 is HOLD evidence | Keep v2 runtime, but backport safe v3 advantages as artifact-led tools and wrapper tests. |
| QWAVE | Evidence only until gate changes | Convert HOLD into a three-lane hold-exit ladder: reconcile, diagnose, then isolated candidate. |
| DoppelGround | USE MODE but blocked by gitleaks | Internal use can resume after false-positive ledger; public/export use still requires sanitized export. |
| ReviewGround | Dormant / scattered | Revive as governed knowledge compiler plus Obsidian UI/export surface. |
| DeepWiki | External helpful tool | Add `.devin/wiki.json` steering so DeepWiki indexes NEXUS around real architecture surfaces. |
| GeniusTurtle | UI-only future layer | Wake as visible NEXUS layer and model-access lab shell; governance remains in NEXUS. |

## TWAVE: Securely Add Old Advantages To Current v2

Do not replace `nexus_os/twave` with QWAVE v3. Instead, add a safe backport lane:

1. `twave_compat_inventory`: compare v2 classes against QWAVE v3 concepts.
2. `qwave_artifact_ledger`: ingest saved QWAVE truth-lab artifacts as evidence records, not runtime behavior.
3. `twave_wrapper_smoke`: expose `/twave/*` smoke endpoints with no algorithm mutation.
4. `twave_v3_replay_readonly`: run QWAVE scripts only against saved artifacts or bounded fixtures.
5. `twave_v2_policy_patch`: only after tests pass, backport non-invasive improvements: manifest schema, artifact comparison, diagnostic summaries, and stricter import-path checks.

Allowed now:

- artifact summarizers
- saved-result comparators
- wrapper smoke tests
- manifest readers
- compatibility reports

Not allowed yet:

- Triton/CUDA kernels
- new GPU-heavy sweeps
- runtime contract rewrite
- model/fixture widening without a proposal

## QWAVE: Turn `KEEP HOLD` Into Motion

The problem is not that HOLD exists. The problem is treating HOLD as an excuse for no progress. Convert it into an active ladder:

### Lane A - Reconcile

Purpose: make the accepted record clean.

Tasks:

- Verify `m8` artifact paths and hashes.
- Rebuild the comparison report from saved JSON only.
- Confirm Qwen `chi=32/64`, `max_modules=8` evidence still ranks `4-bit WHT > 3-bit WHT > 2-bit WHT > 2-bit direct`.
- Produce a one-page "accepted evidence floor" note.

Exit condition: no unresolved artifact/report mismatch.

### Lane B - Active Diagnosis

Purpose: understand the Llama residual gap without redesigning.

Tasks:

- Run Distance-Preference Audit on existing artifacts.
- Compare Llama/Qwen sensitivity at the same `chi`.
- Keep runs sequential; never run `chi=32` and `chi=64` at the same time on the same GPU.
- Report only diagnostic signals, not production claims.

Exit condition: one bounded design question with a success rule and stop rule.

### Lane C - Isolated Candidate

Purpose: allow movement after evidence is clean.

Tasks:

- Create an isolated branch/worktree.
- Implement one candidate only.
- Run exact regression suite and downstream sanity checks.
- Promote only via NEXUS governance approval.

Exit condition: candidate improves target gap without violating storage, ABI, or runtime constraints.

## DoppelGround + ReviewGround: Resume Internal Use

The gitleaks report is not a reason to freeze internal DoppelGround forever. The sampled findings are run tokens and hook-event artifacts, and the existing `.gitleaks.toml` already tries to suppress those classes.

Updated gate:

- Internal use: allowed after a redacted false-positive ledger is generated.
- Repo import into NEXUS: still blocked until only sanitized exports are used.
- Public release: blocked until the false-positive allowlist is reviewed and a clean public scan is produced.

ReviewGround should become the compiler layer:

```text
raw source -> source brief -> candidate note -> draft wiki -> review packet -> published wiki -> Obsidian / DeepWiki / NEXUS graph
```

Existing assets to reuse:

- `upload/wiki_pipeline.py`
- `DERDDRE/v4/handbook/07_WIKI_AND_REVIEWGROUND.md`
- `DERDDRE/v4/dashboard/static/src/pages/Wiki.jsx`
- `DoppelGround/agents/sync-protocol.md`
- `DoppelGround/agents/operator-playbook.md`

New NEXUS target shape:

```text
docs/wiki/
  raw/              # immutable source captures, no edits
  briefs/           # source summaries with hashes
  drafts/           # generated ReviewGround pages
  published/        # approved wiki pages
  graph/            # wiki graph JSON and validation outputs
  obsidian/         # exported vault view
```

## DeepWiki + Karpathy Wiki Distillation

DeepWiki is useful as a repo navigator. It is not canonical truth.

Use DeepWiki for:

- repo structure orientation
- cross-repo questions
- generated wiki outlines
- quick architecture review prompts

Do not use DeepWiki for:

- final readiness claims
- secret/audit signoff
- replacing local tests
- writing canonical state automatically

Karpathy-style wiki lesson for NEXUS:

- Keep raw sources immutable.
- Keep generated wiki pages separate from source.
- Make schema/rules explicit.
- Run lint/repair loops continuously.
- Let the human/operator promote drafts.

This maps directly to NEXUS:

- Raw = DoppelGround source captures.
- Wiki = ReviewGround compiled pages.
- Schema = frontmatter/truth-layer policy.
- Lint = `nexusctl wiki check`.
- Promotion = Governor approval + VAP/audit record.

## GeniusTurtle: Wake As Visible Layer + Model Lab Shell

GeniusTurtle has enough base to become a visible NEXUS layer:

- local control API exists at `GeniusTurtle/control_desk/api/main.py`
- GemmaTurtle runtime evidence exists around `llama-server.exe` on `127.0.0.1:8080`
- `opusmanSEEKv4/GeniusTurtle/design.md` gives the newer operator UI direction
- gitleaks report is clean

Recommended immediate surface:

```text
GeniusTurtle UI
  /status           # NEXUS, Guard Plane, local model, OpenClaw health
  /agents           # trust, sessions, heartbeats
  /models           # local/provider model availability and smoke tests
  /twave            # wrapper diagnostics only
  /reviewground     # wiki graph, drafts, frontmatter issues
  /lab              # model merge/train/fine-tune job cards
```

Unsloth-inspired lab, governed NEXUS version:

```text
dataset card -> recipe card -> preflight -> training/merge job -> eval -> registry -> rollback point
```

Hard rules:

- No training job without dataset hash and recipe hash.
- No model merge without safety eval and rollback artifact.
- No UI action writes canonical state directly.
- No local GPU-heavy run while Streamlabs/OBS/active workloads are protected.
- Every output becomes an evidence packet before it becomes a model route.

## S-P-E-W / KAIJU Mapping

| Contract | S-P-E-W layer | KAIJU gate |
|---|---|---|
| TWAVE wrapper | Session + Project | Runtime safety, import-path, bounded smoke test |
| QWAVE evidence ledger | Project + Wisdom | Evidence reconciliation, no redesign without approval |
| DoppelGround source brief | Source + Project | Leak classification, source hash, provenance |
| ReviewGround wiki page | Project + Wisdom | Frontmatter validity, contradiction lint, approval packet |
| GeniusTurtle UI action | Session | Operator intent check, read-only by default |
| Model Lab job | Project + Experience | Dataset hash, recipe hash, resource safety, eval gate |

## Immediate Execution Tasks

1. Add DeepWiki steering file: `.devin/wiki.json`.
2. Generate redacted DoppelGround false-positive ledger from `gitleaks-report.json`.
3. Create `docs/wiki/` skeleton with `raw`, `briefs`, `drafts`, `published`, `graph`, and `obsidian`.
4. Move `upload/wiki_pipeline.py` into a reviewed tool path only after dependency check.
5. Add a `nexusctl wiki check` compatibility task or document the missing command if not implemented.
6. Add a TWAVE/QWAVE artifact ledger script that reads saved artifacts only.
7. Add `/twave/health` and `/twave/diagnostics` smoke tests before any algorithm change.
8. Create GeniusTurtle NEXUS adapter plan: status, models, reviewground, lab.
9. Build model lab job-card schema before any Unsloth-style execution.
10. Reconcile `01_PROJECT_STATE.md` and `knowledge.md` after these lanes are accepted.

## Architecture Decision

Adopt a visible-layer strategy:

- NEXUS is the brain, governor, and audit spine.
- TWAVE is the governed low-VRAM/thermodynamic execution adapter.
- QWAVE is the evidence and experimental science lane.
- DoppelGround is the source intake and mission/evidence producer.
- ReviewGround is the compiled wiki/review/promotion layer.
- DeepWiki is external repo documentation assist.
- Obsidian is the human-readable graph UI.
- GeniusTurtle is the operator-facing control surface and model lab shell.

Actionable insight: the next upgrade is not a big merge. It is a controlled activation of dormant strengths through narrow contracts that make each layer useful without letting any layer become the uncontrolled source of truth.

## Sources Consulted

- Local: `docs/handoff/NEXUS_TWAVE_QWAVE_DOPPLEGROUND_GENIUSTURTLE_INTEGRATION_SCAN_2026-05-26.md`
- Local: `C:\Users\speci.000\Documents\QWAVE\twave\ROADMAP.md`
- Local: `C:\Users\speci.000\Documents\QWAVE\twave\docs\final_verdict_proposals.md`
- Local: `C:\Users\speci.000\Documents\DoppelGround\.gitleaks.toml`
- Local: `C:\Users\speci.000\Downloads\DeepWiki NEXUS MCP Integration and Capability Report.md`
- Local: `C:\Users\speci.000\Downloads\DERDDRE\v4\handbook\07_WIKI_AND_REVIEWGROUND.md`
- Local: `C:\Users\speci.000\Documents\opusmanSEEKv4\GeniusTurtle\design.md`
- Web: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- Web: `https://docs.devin.ai/work-with-devin/deepwiki`
- Web: `https://docs.unsloth.ai/`
