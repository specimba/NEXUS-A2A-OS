---
id: NODE-MIG-DEVIN_KIMI_GUARD_PLANE_NEXT_MISSION_2026_05_24
authority_scope: experimental
origin_sha256: e62ec6e3941c7eece9e6ec2dea61f2a9537b7c719abe14861472aa40b98e5139
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-E76F23
---
# Devin/Kimi Guard Plane Next Mission - 2026-05-24

## Mission Summary

<!-- CANARY: f44b206b981009d678b0490ffd282992 -->
Continue from commit `d3a8f50` (`Fix Guard Plane Service integration bugs`) and convert the Guard Plane work from "working prototype plus local classifier artifact" into a governed, testable, repo-hygienic NEXUS security subsystem.

The current Guard Plane direction is valid: `models/guards/guard_plane_service.py` places `MetaAttackDetector` in front of CSV injection regex checks, query-type classification, prompt routing, and Ollama guard models. The next mission is not to redesign that stack. The next mission is to prove it, harden it, document its boundaries, and decide how the classifier artifact is managed.

## Verified Starting Point

- Current verified HEAD during this handoff: `d3a8f50`.
- Commit `d3a8f50` changed two files:
  - `models/guards/guard_plane_service.py`
  - `docs/handoff/ANTIGRAVITY_CLAIMS_VERIFICATION_2026-05-24.md`
- Focused detector tests passed:
  - `python -m pytest tests/security/test_meta_attack_detector.py -q`
  - Result: `16 passed, 1 warning`
- `models/guards/query_classifier.pkl` exists in the live checkout and is currently untracked:
  - Size: `845664` bytes
  - Type after unpickle: `sklearn.pipeline.Pipeline`
  - Exposes `predict_proba`
  - Exposes classifier classes:
    - `attack_ernie`
    - `benign_adversarial_benign`
    - `benign_domain_specific`
    - `benign_edge_cases`
    - `benign_ernie_corpus`
    - `benign_gray_area`
    - `benign_simple`
    - `tamas`
    - `v7`
- `guard_plane_service.py` imports successfully and loads the classifier.
- Smoke evidence without starting the server:
  - Benign HTTPS query classified through `classify_query`.
  - TAMAS-style reviewer impersonation blocked by `MetaAttackDetector` prefilter.
  - CSV/SQL injection row blocked by `csv_regex` prefilter.

## Correction To Previous Summary

The prior summary said `query_classifier.pkl` does not exist yet. That is stale now.

The correct live-state claim is:

`models/guards/query_classifier.pkl` exists locally, loads successfully, but is untracked. The next agent must decide, with evidence, whether to:

1. Track it as a small reproducible guard artifact with a manifest.
2. Keep it untracked and add a reproducible training script plus manifest.
3. Regenerate it and compare metrics/hash before deciding.

Do not silently leave the artifact ambiguous.

## Mandatory Grounding Before Work

Read these files before editing:

- `AGENTS.md`
- `01_PROJECT_STATE.md`
- `knowledge.md`
- `docs/handoff/NEXUS_LOCAL_GROUNDING_REFRESH_2026-05-24.md`
- `docs/handoff/META_ATTACK_DETECTOR_V3_GAPS_2026-05-24.md`
- `docs/handoff/BOUNCER_MODEL_MATRIX_2026-05-24.md`
- `docs/handoff/ANTIGRAVITY_CLAIMS_VERIFICATION_2026-05-24.md`
- `tests/security/test_meta_attack_detector.py`
- `models/guards/guard_plane_service.py`

Then run and record:

```powershell
git status --short --branch
git rev-parse --short HEAD
python -m nexusctl doctor memory --report-only
python -m nexusctl doctor version --report-only
python -m nexusctl cycle-check
```

If `cycle-check` halts on infrastructure/Ollama, report it as a live blocker. Do not hide it.

## Workstream 1 - Guard Plane Service Hardening

Keep the architecture:

`User Query -> MetaAttackDetector -> CSV Injection Prefilter -> Query Classifier -> Routed Prompt -> Ollama Guard Model`

Required fixes or confirmations:

1. Confirm `OLLAMA_HOST` default is correct for the active local stack. The service currently defaults to `127.0.0.1:11435`; previous NEXUS memory mentions canonical Ollama host handling around `11434`, while this branch may intentionally use `11435`. Resolve by live evidence, not assumption.
2. Add a clear startup health result for missing Ollama instead of pretending all models are available.
3. Preserve the 503 queue-full retry behavior and 500 model-loading retry behavior.
4. Add a bounded request timeout path that returns structured degraded status, not raw exception text.
5. Ensure `/v1/batch` has a maximum batch size and pacing. The current 0.5 second pacing is good, but unbounded batch length can still burn local resources.
6. Do not expose this service publicly. It is local/internal unless explicitly wrapped by NEXUS governance.
7. Prefer canonical package imports over permanent `sys.path` hacks. If the path shim remains necessary during branch-layout drift, document the reason and add a test proving the intended import target.

## Workstream 2 - Classifier Artifact Policy

Resolve the untracked `models/guards/query_classifier.pkl` state.

Required outputs:

1. A manifest next to the classifier, for example `models/guards/query_classifier.manifest.json`, with:
   - artifact filename
   - sha256
   - byte size
   - created timestamp if known
   - training script path
   - dataset sources
   - class labels
   - validation metrics
   - known failure cases
2. A reproducibility note in `docs/handoff`, unless the manifest is enough.
3. A decision:
   - If the pickle is tracked, justify why this small binary artifact is acceptable.
   - If the pickle stays untracked, ensure `.gitignore` and regeneration instructions are explicit.
4. A safe load test that never executes arbitrary external pickle content. Only load the local artifact produced by this repo workflow.

## Workstream 3 - ERNIE / BOUNCER Benchmark Integration

Turn the ERNIE and BOUNCER work into repeatable evidence:

1. Identify the exact benchmark corpus used for the current classifier.
2. Separate benign, gray-area, TAMAS, V7, and ERNIE attack sets.
3. Produce a report-only benchmark command that writes JSON/Markdown evidence under a reviewed report path.
4. Track false positives and false negatives separately.
5. Require special attention to benign false positives; `61df031` claims work on lowering ERNIE benign false positives below 10%.
6. Never claim a global detection percentage unless the dataset, sample count, prompt/model route, and model version are recorded.

## Workstream 4 - Tests

Add focused tests before broad integration:

1. `MetaAttackDetector` regression tests for:
   - reviewer impersonation
   - manager/admin authority spoofing
   - approval bypass wording
   - benign creative/meta prompts that should not trigger
2. Guard Plane service tests for:
   - classifier load success
   - classifier missing fallback
   - TAMAS prefilter blocks before Ollama
   - CSV/SQL prefilter blocks before Ollama
   - low-confidence route fallback
   - `/v1/health` reflects classifier and Ollama status accurately
   - `/v1/batch` enforces maximum length
3. Mock Ollama calls. Do not require a live local model for unit tests.
4. Only run the full NEXUS suite if touching core bridge/governor/vault/router/GMR paths. Otherwise, run focused tests and clearly report that full suite was not run.

Suggested minimum gate:

```powershell
python -m pytest tests/security/test_meta_attack_detector.py -q
python -m pytest tests/security/test_guard_plane_service.py -q
python -m py_compile models/guards/guard_plane_service.py nexus_os/security/meta_attack_detector.py
```

## Workstream 5 - NEXUS Governance Boundary

Do not let the Guard Plane become a parallel, unmanaged security authority.

Required boundary decisions:

1. Is Guard Plane a prefilter library, a local FastAPI service, or middleware behind the canonical NEXUS bridge?
2. If it runs on port `7352`, confirm it does not conflict with the existing governance API expectation.
3. If it is behind NEXUS governance, define how TrustKernel/KAIJU/VAP audit receives:
   - query hash
   - block category
   - confidence
   - model route
   - final verdict
4. If it remains standalone, label it as experimental/local-only and prevent public exposure.

## Workstream 6 - Documentation And State Hygiene

Update only the documents that can be supported by fresh evidence.

Allowed documentation outputs:

- One focused handoff report under `docs/handoff/`.
- One classifier manifest under `models/guards/`.
- Optional test report artifact if generated by a script.

Avoid:

- New duplicate canonical state docs.
- New broad claims in `01_PROJECT_STATE.md` unless tests and HEAD are fresh.
- "617 passed", "642 passed", "670 passed", or any other baseline claim without a current command log.
- Storing reports under `C:\tmp`.

## Git Discipline

No `git add .`.

Before staging, print:

```powershell
git status --short --branch
```

Stage only explicit reviewed paths. Candidate paths may include:

```powershell
git add -- models/guards/guard_plane_service.py
git add -- models/guards/query_classifier.manifest.json
git add -- tests/security/test_guard_plane_service.py
git add -- docs/handoff/<final-report>.md
```

Only add `models/guards/query_classifier.pkl` if the artifact policy says tracking it is intentional and safe.

Do not stage:

- `.env`
- backups
- raw downloaded dumps
- model weights
- GGUF files
- virtual environments
- generated caches
- raw DoppelGround sessions
- broad `upload/` material

## Acceptance Criteria

This mission is complete only when all are true:

1. `d3a8f50` changes are verified against the live checkout.
2. `query_classifier.pkl` status is resolved with manifest and explicit policy.
3. Guard Plane service has focused tests for prefilter, classifier fallback, health, and batch limits.
4. Ollama unavailable/queue-full/model-loading paths return structured degraded output.
5. Port/governance ownership is documented: standalone local service vs canonical NEXUS bridge integration.
6. No public exposure, no secret leakage, no model weight staging.
7. Final report lists exact commands run and exact files changed.
8. If infrastructure blocks tests, the blocker is recorded with evidence instead of converted into a success claim.

## Final Report Template

Use this structure:

```markdown
# Guard Plane v1.3 Verification Report

## Live State
- Branch:
- HEAD:
- Dirty state:
- Relevant untracked artifacts:

## Changes Made
- 

## Classifier Artifact Decision
- Decision:
- Hash:
- Manifest:
- Repro path:

## Verification
- Command:
- Result:

## Remaining Risks
- 

## Next Action
- 
```

