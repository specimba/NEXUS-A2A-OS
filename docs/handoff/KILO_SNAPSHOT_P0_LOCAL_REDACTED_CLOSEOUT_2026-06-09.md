# Kilo Snapshot P0 Local Redacted Closeout - 2026-06-09

## Scope

Closes P0 at aggregate level without emitting exact sensitive paths or secret values. The preserved high-value matrices intentionally redact P0 paths, so exact path review cannot be reconstructed from current handoff artifacts without rerunning raw forensic inventory.

## Counts

- Selected rows: `46`
- Files with secret-like patterns: `19`
- Missing now in source scan: `0`
- Oversize skipped: `0`
- Decode failures: `0`

## Prefix Counts

| Prefix | Rows |
|---|---:|
| `benchmarks` | `3` |
| `datasets` | `2` |
| `docs` | `14` |
| `evidence` | `1` |
| `logs` | `25` |
| `tasks` | `1` |

## Pattern Classes

| Pattern class | Count signal |
|---|---:|
| `api_key_generic` | `19` |
| `github_token` | `1` |
| `password_field` | `1` |

## Decision

- P0 is not releaseable as raw body content.
- P0 rows stay local sensitive hold; external agents get sanitized summaries only.
- The redaction worked: exact sensitive paths are not available in the handoff artifacts.
- Keeping the Kilo snapshot keeps duplicate historical sensitive material. Deleting it after approval reduces duplicate sensitive-at-rest exposure.
- Do not regenerate unredacted path reports unless there is a specific recovery need.
