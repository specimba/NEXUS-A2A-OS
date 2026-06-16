---
id: NODE-MIG-2026_05_20_ALPHA_BRANCH_COMPARISON
authority_scope: experimental
origin_sha256: e5830e3346991c927113c231271e4a1bd07c35038c4a34719a04324e0bbaad94
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-F7219A
---
# Alpha Branch Tree Comparison - 2026-05-20

<!-- CANARY: d9f09d7bd197bc9265e95be58901108f -->
Scope: private `specimba/nexusalpha` only.

## Branch Reality

| Pair | Merge Base | Decision |
| --- | --- | --- |
| `origin/main` -> `origin/release/v3.1-dashboard` | none | Do not merge directly. Use tree-level selective port only. |
| `origin/main` -> `origin/DASHBOARD-GLM51` | none | Do not merge directly. Use tree-level selective port only. |
| `origin/release/v3.1-dashboard` -> `origin/DASHBOARD-GLM51` | `b50886f` | Safe to inspect by diff, but still not safe to merge wholesale. |

## Diff Scale

| Compare | Changed Paths | Shortstat |
| --- | ---: | --- |
| `main` -> `release/v3.1-dashboard` | 101 | 35,962 insertions / 5,809 deletions |
| `main` -> `DASHBOARD-GLM51` | 188 | 39,495 insertions / 17,712 deletions |
| `release/v3.1-dashboard` -> `DASHBOARD-GLM51` | 120 | 13,599 insertions / 21,969 deletions |

## What Was Ported

- Custom dashboard API and UI files from `DASHBOARD-GLM51`.
- MCP Hub API and UI files from `DASHBOARD-GLM51`.
- Config/audit/metrics support routes needed by dashboard workflows.
- Navigation wiring for `dashboards`, `mcp`, and `config` tabs while preserving the existing `providers` tab.
- `PostHogProvider` with environment-gated no-op behavior when analytics keys are absent.
- `src/nexus_os/security/sanitizer.py` from `main`, plus focused tests.

## What Was Rejected

- `.env` changes.
- `upload/` artifacts and raw evidence bundles.
- Dashboard branch deletions of Supabase auth pages and server/client helpers.
- Dashboard branch deletion of provider/key management routes.
- Dashboard branch Prisma regression that removed encrypted API-key fields.
- Generic `SECURITY.md` from unrelated `main` because it contains placeholder version policy.

## Hardening Applied During Port

The source dashboard branch stored MCP connector keys as an `apiKey` database field while the UI said the keys were encrypted. This port does not persist raw MCP keys. It stores only `apiKeyRef`, an environment-variable reference, and reports `hasApiKeyRef` to the UI.

## Required Gates

- `bun install` to refresh `bun.lock` after dependency additions.
- `bun run lint`.
- Focused Python tests for MCP and sanitizer.
- Secret-pattern check that `.env` is unchanged and not secret-bearing at branch tip.
