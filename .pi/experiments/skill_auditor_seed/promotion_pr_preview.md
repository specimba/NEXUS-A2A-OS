# Promotion PR Preview — papers09 SkillAuditor Seed → DEFAULT_RULES

**Status: PLANNING ONLY.**
**Do not apply without explicit operator approval.**
**Author of seed:** NEO-agent deep-search pass, 2026-06-21.

This document is a self-contained "future-PR" snapshot so an operator can review a complete diff before merging anything into `nexus_os/governor/skill_auditor.py::DEFAULT_RULES`. Do NOT execute any of the steps in this document unless `--load-papers09-seed` is granted and the body-PDF read is completed.

## Required Pre-Conditions Before Any Code Change

1. Read the body of **every paper in `papers09/`** (89 files) and capture at least:
   - Abstract page (page 1).
   - List of evaluation metrics.
   - Claim statements quoted text-exact.
2. Append `provenance.citation` to each rule in `attack_taxonomy_seed.yaml`.
3. Promote `evidence_grade` to `E1+`.
4. Operator signs off on each rule ID, severity, and remediation text.

## Proposed Diff (no execution)

### File 1: `nexus_os/governor/skill_auditor.py`

- Append 24 rules below `DEFAULT_RULES` block (line 369).
- Each rule added is a full `DetectionRule(...)` block.
- Initials:
  - JAILBREAK_PREFIX_INJECTION
  - JAILBREAK_SYSTEM_PROMPT_SPOOF
  - JAILBREAK_INSTRUCTION_HIJACK
  - JAILBREAK_POLICY_COUNTERFEIT
  - JAILBREAK_ROLEPLAY_ESCALATION
  - JAILBREAK_AUTHORITY_PRESSURE
  - JAILBREAK_MULTITURN_AWAI
  - JAILBREAK_PAYLOAD_SMUGGLE
  - JAILBREAK_OUTPUT_CHANNEL_LOCK
  - JAILBREAK_CROSS_LANGUAGE_EVASION
  - JAILBREAK_ENCRYPT_OBFUSCATE
  - JAILBREAK_HARMFUL_FEW_SHOT_SEED
  - JAILBREAK_NARRATIVE_REFRAMING
  - JAILBREAK_ACADEMIC_PRETEXT
  - JAILBREAK_OUTPUT_SUFFIX_NO_HEDGE
  - JAILBREAK_SANDBOX_PRETEXT
  - JAILBREAK_DATE_AUTHORITY_PRETEXT
  - JAILBREAK_CREDENTIAL_PIVOT
  - JAILBREAK_DIRECTIVE_STACKING
  - JAILBREAK_NEGATION_SMUGGLE
  - JAILBREAK_FABRICATION_CLAIMS
  - JAILBREAK_PERMISSION_GRANT
  - JAILBREAK_CODE_COMMENT_CHANNEL
  - JAILBREAK_PLACEHOLDER_CATEGORY_FILL

### File 2: `nexus_os/governor/constitution.yaml` (already referenced in `knowledge.md`)

- Add 12 new attack families, each with rule-id mapping.
- Include severity ceiling (CRITICAL: prefix_injection / system_prompt_spoof / credential_pivot).

### File 3: `tests/governor/test_skill_auditor.py`

- Add fixture `def test_papers09_seed_loads(): ...` (uses `--load-papers09-seed`).
- Add `def test_papers09_seed_coverage(): ...` that parametrises all 24 rule_ids.
- Add `def test_placeholder_category_deleted_under_promotion(): ...`.

### File 4: `docs/research/PAPERS09_STRATEGIC_ASSESSMENT_2026-06-20.md` (already present)

- Update §4 Insertion Plan table to mark P0 entries as `promoted` after the merge.
- Add a footnote pointing to this promotion PR preview.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| False positives (high-allow-content flagged) | Run `--load-papers09-seed` only in adversarial lanes (DoppelGround) by default; mainlanes disabled. |
| Pattern overlap with `DERDDRE` and `CSI` cascades (per `knowledge.md:177-180`) | Each new rule references `pairs_with` and routes through the same L0 pre-processor. |
| Rule injection of unsafe regex | `re.compile` only on patterns that pass `pytest` corpus with F1 ≥ 0.85. |
| Configuration drift across lanes | All CRITICAL rules contribute to `constitution.yaml`; pinned via `constitution_version` field. |

## Verification Commands (post-merge, in venv only)

```text
# Apply proposal rules
python -m pytest tests/governor/test_skill_auditor.py -q -k "papers09"
python -m nexusctl doctor --suggest-fixes
python -m nexusctl stress-lab --track security

# Confirm no canonical mutation if operator declines:
git -C "C:\Users\speci.000\Documents\NEXUS" diff --stat nexus_os/governor/skill_auditor.py
```

## Status

This PR preview is **DRAFT** and **NOT** auto-applied.
