# Kilo Snapshot P0 Sensitive Aggregate Scan - 2026-06-08
## Scope
Selected `P0_sensitive_hold` + `live_differs_from_snapshot_untracked` rows from the Kilo byte comparison. Sensitive paths were loaded only in process memory; this report does not emit exact sensitive filenames or secret values.
## Counts
- Selected rows: `46`
- Files scanned: `46`
- Files with secret-like patterns: `19`
- Missing now: `0`
- Oversize skipped: `0`
- Text/read failures: `0`

## Prefix Counts
| Prefix | Rows | Bytes | Secret-like matches |
|---|---:|---:|---:|
| `logs` | 25 | 895013 | 76 |
| `docs` | 14 | 684209 | 81 |
| `benchmarks` | 3 | 6366 | 1 |
| `datasets` | 2 | 11350 | 1 |
| `evidence` | 1 | 133165 | 0 |
| `tasks` | 1 | 4033 | 1 |

## Pattern Counts
| Pattern | Files/count signal |
|---|---:|
| `api_key_generic` | 19 |
| `password_field` | 1 |
| `github_token` | 1 |

## Safety
- Exact sensitive paths are intentionally omitted.
- Secret values are intentionally omitted.
- No live file, Git state, or Kilo quarantine file was modified.
