# skill_auditor_seed — Non-Canonical Experiment Lane

**Status:** NON-CANONICAL / EXPERIMENTAL / OPT-IN
**Generated:** 2026-06-21
**Source:** ARCHIVIST/PAPERS/papers09/ADVERSARIAL DÉJÀ VU JAILBREAK DICTIONARYmethods.txt (397 unique skills, 25 attack families)

## Files

| File | Purpose |
|------|---------|
| `attack_taxonomy_seed.yaml` | 24 draft `DetectionRule` entries mirroring `nexus_os/governor/skill_auditor.py::DetectionRule`. Each carries a `provenance` block referencing source `skill_name` and visible `row_index` anchors. |
| `attack_taxonomy_index.json` | Machine-readable category index; aggregates rule_ids + attack families + open residuals. |
| `loader_stub.py` | Advisory-only Python loader. Returns rule list as data. **No canonical mutation.** |
| `promotion_pr_preview.md` | Exact diff a future operator must apply if/when promoting this seed into `SkillAuditor.DEFAULT_RULES`. |

## Hard Lock (Non-Canonical)

1. `SkillAuditor.__init__` is unchanged. The seed is **not** loaded by default.
2. Loader requires the `--load-papers09-seed` gating token.
3. `canonical: false` in the JSON index. `auto_load: false`.
4. `evidence_grade` is `E0` on every rule. Body-PDF read is required for `E1+` promotion.
5. `metadata_conditions` per rule retain provenance categories so evidence can be re-derived.

## Categories (12)

`prompt_injection | instruction_hierarchy | policy_counterfeit | jailbreak_role_play | authority_pressure | multi_turn_manipulation | payload_smuggling | obfuscation_encoding | harmful_seeding | output_manipulation | safety_smuggling | credential_pivot`

Each category aggregates 1–4 rules that cover its representative skill families from the source.

## Source Provenance Tracking

The YAML is designed so each rule's `provenance.source_skill_names` and `source_row_indexes_visible` point to the exact bullets from the original `.txt`. Promotion requires adding a `provenance.citation` field with the body PDF page or paragraph index once a body read is performed.

## Promotion Path (Operator-Approved)

The `promotion_pr_preview.md` file in this folder details the required changes:

1. Add all 24 rules to a candidate list (use `loader_stub.py --dry-run` to print the order).
2. Add a category→severity mapping in `constitution.yaml` so the rules appear under correct lanes.
3. Run the existing `tests/governor/test_skill_auditor.py` against the new rules.
4. Update `constitution.yaml` and `tests/governor/test_skill_auditor.py` to assert rule IDs.
5. After body-PDF read promotes evidence grade, replace `JAILBREAK_PLACEHOLDER_CATEGORY_FILL` with real rules.

## How to Inspect This Folder (read-only)

```text
Test-Path "C:\Users\speci.000\Documents\NEXUS\.pi\experiments\skill_auditor_seed"

# Confirm no canonical mutation:
Test-Path "C:\Users\speci.000\Documents\NEXUS\nexus_os\governor\skill_auditor.py"
Get-Content "C:\Users\speci.000\Documents\NEXUS\nexus_os\governor\skill_auditor.py" | Select-String "DEFAULT_RULES"

# Dry-run the loader (does NOT mutate anything):
python .pi/experiments/skill_auditor_seed/loader_stub.py --path .pi/experiments/skill_auditor_seed/attack_taxonomy_seed.yaml --dry-run
```

## Risks Acknowledged

- These patterns arm the `SkillAuditor` against an adversarial space we already observe in production logs (per `knowledge.md:170-177` Cascade L0 architecture).
- A false-positive here is preferable to a false-negative on a CRITICAL-severity rule — see `JAILBREAK_CREDENTIAL_PIVOT` and `JAILBREAK_SYSTEM_PROMPT_SPOOF`.
- We do **not** add destructive actions. The loader is read-only by construction.

## Neon-Phase Promotion PR Preview is in `promotion_pr_preview.md`.
