---
id: NODE-MIG-DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_TRIAGE_2026_05_26
authority_scope: experimental
origin_sha256: 6ac0829846cae1e37bbef3aee989305f181a6c8689459f9371ea2852a89faa7a
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-74D713
---
# DoppelGround Gitleaks False-Positive Triage - 2026-05-26

## Scope

<!-- CANARY: c1e0c908534c03e3097c24b30a27be14 -->
Read-only triage of:

- `C:\Users\speci.000\Documents\DoppelGround\gitleaks-report.json`
- `C:\Users\speci.000\Documents\DoppelGround_m0_freeze_current\gitleaks-report.json`
- `C:\Users\speci.000\Documents\DoppelGround\.gitleaks.toml`

No raw token-like values are included in this note.

## Result

The report contains `1919` findings in both the main and frozen DoppelGround copies.

All sampled findings use rule:

- `generic-api-key`

The sampled matches are dominated by generated run identifiers and hook-event artifacts, for example:

- `run_token` fields in drill-engine JSON run files
- `hook_events.jsonl`
- `remediation_candidates.jsonl`
- project-fit/report metadata lines

The existing `.gitleaks.toml` already documents the intended suppression class:

- DoppelGround run token format: `DR-XX_YYYYMMDD_HHMMSS_RANDOM`
- session IDs
- model hash patterns
- quantization suffixes
- research timestamps
- generic placeholder/fixture stopwords

## Interpretation

This supports the operator claim that the current `1919` finding class is a false-positive class, not evidence of provider credential leakage.

However, the correct engineering conclusion is not "ignore gitleaks." The correct conclusion is:

- internal DoppelGround/ReviewGround work may resume using a redacted false-positive ledger
- public release still requires a clean or reviewed scan
- raw DoppelGround trees should not be imported into NEXUS
- sanitized exports are allowed after source hashes and triage metadata are recorded

## Recommended Gate Change

Replace the old hard blocker:

```text
DoppelGround blocked by 1919 gitleaks findings
```

with a more precise gate:

```text
DoppelGround internal use allowed after false-positive ledger.
Public/export use requires reviewed suppressions plus clean public-target scan.
```

## Next Actions

1. Generate a machine-readable false-positive ledger with file, rule, line, classification, and redacted preview.
2. Add or refine `.gitleaks.toml` allowlist patterns for DoppelGround run tokens and hook-event fixture files.
3. Re-run gitleaks against a public-target export folder, not the full noisy research tree.
4. Store the clean public-target report beside the export packet.

## Safety Note

This triage did not prove that every one of the 1919 findings is harmless. It proved that the sampled class and existing allowlist strategy are consistent with generated research/run-token false positives. Public release still needs a target-specific clean scan.
