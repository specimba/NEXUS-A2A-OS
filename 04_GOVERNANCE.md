# 04 — GOVERNANCE (Canonical v3.0)
**Status**: CODE_CONFIRMED | **Tag**: m3-hardened

## Authorization Pipeline
`check_access()` → KAIJU 4-Var Gate → Compliance → VAP Audit

## KAIJU 4-Variable Gate
| Variable | Values | Rule |
|---|---|---|
| Scope | self, project, system | Clearance-bound |
| Intent | Free-text (10+ chars) | Keyword match + HOLD on mismatch |
| Impact | low, med, high, critical | Critical → HOLD |
| Clearance | reader, contributor, admin | Deny-by-default |

## Non-Negotiable Invariants
1. `null` ≠ `0`. Null never enters averages.
2. Harm is non-compensatory (`R > Rcrit` → `-1`).
3. Refusal affects `availability`, not `trust`.
4. Cold-path never blocks hot-path.
5. All decisions append to VAP chain (SHA-256).
