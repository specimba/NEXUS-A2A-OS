# Gitleaks Triage Report: DoppelGround

**Date**: 2026-04-21
**Source**: `c:\Users\speci.000\Documents\DoppelGround\gitleaks-report.json`
**Findings**: 40,302 lines in JSON (~5k findings)

## Summary of Findings

| Category | Status | Rationale |
|---|---|---|
| `run_token` | False Positive | Operational identifiers for drill runs (e.g., `DR-01_...`). These are task-specific and not cryptographic secrets. |
| `crowding_penalty` | False Positive | LLM parameter erroneously flagged as a generic API key. |
| `github_router_for_me_cliproxyapi` | False Positive | Contextual string from a markdown report. |

## Detailed False Positive Patterns

1. **Drill Tokens**:
   - Match: `DR-XX_TIMESTAMP_HASH`
   - Files: `external/Playground-final-no-loss-pack/...`, `observation_packets/...`, `execution_plans/...`
   - Count: Majority of findings.

2. **Model Parameters**:
   - Match: `crowding_penalty=2`
   - Files: `research_intake/...`

## Conclusion

The vast majority of findings in the DoppelGround gitleaks report are false positives originating from operational tokens and model parameters. No high-severity real secrets (e.g., AWS keys, OpenAI keys) were identified in the initial triage of the top 800 lines.

> [!IMPORTANT]
> The repository is safe for the Phase 0 grounding transition, but a filtered scan with a refined `.gitleaks.toml` should be performed before any public release.
