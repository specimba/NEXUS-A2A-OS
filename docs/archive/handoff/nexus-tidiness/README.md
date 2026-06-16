---
id: NODE-MIG-README
authority_scope: local-canonical
origin_sha256: 58650f899a4c103ca9bbc0de38169ac586ab11e8c6dd44902c881463486a0ed0
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B33563
---
# NEXUS Tidiness Run 2026-05-21-001353

## Scope

This run is the starting point for a repeatable NEXUS cleanup and tidiness protocol.
It inventories local file sprawl before moving anything, keeps reports inside the
NEXUS repository tree, and protects research/data/secrets from accidental Git
publication.

## Rollback Point

- Source checkout: `C:\Users\speci.000\Documents\NEXUS`
- Starting branch: `codex/specimba/1805mainSpeci`
- Starting HEAD: `f5fe558`
- Local rollback branch: `codex/specimba/rollback-pre-tidiness-20260521-001353`
- Rollback tag: `rollback/pre-tidiness-20260521-001353`
- Remote backup: pushed to `alpha` (`specimba/nexusalpha`)

## Guardrails

1. Do not store important new handoff reports in `C:\tmp`.
2. Do not print, stage, or push `.env` or secret-bearing files.
3. Do not use `git add .`; stage only explicit reviewed paths.
4. Do not recursively delete or move source trees during discovery.
5. Prefer copy-plus-hash verification for external files before any delete.
6. If a file category is uncertain, place it under an ignored `MIXED/` bucket for human review.
7. Keep clone/worktree directories as inventory items unless their branch/PR state is verified.

## Inventory Artifacts

| File | Purpose |
| --- | --- |
| `git-status-before.txt` | Dirty tree snapshot before cleanup actions. |
| `tracked-diff-before.patch` | Local tracked diff snapshot, ignored by Git due size/sensitivity. |
| `rollback-point.txt` | Branch/tag/HEAD rollback coordinates. |
| `source-location-counts.csv` | Size/count summary for `C:\tmp`, Downloads, papers, and NEXUS. |
| `nexus-content-counts.csv` | Size/count summary for NEXUS docs/research/benchmarks/datasets. |
| `nexus-root-inventory.csv` | Top-level NEXUS file/folder inventory. |
| `c-tmp-inventory.csv` | Top-level `C:\tmp` inventory. |
| `c-tmp-recursive-files.csv` | Recursive `C:\tmp` candidate evidence list, ignored by Git due size. |
| `c-tmp-important-file-candidates.csv` | Important-looking `C:\tmp` files. |
| `downloads-top-inventory.csv` | Top-level Downloads inventory. |
| `downloads-nexus-related-candidates.csv` | Downloads items with NEXUS/research/MCP/benchmark signals. |
| `downloads-papers-inventory.csv` | Scientific paper inventory from Downloads. |

## Verified Observations

- NEXUS `docs/research` is small compared with the actual local research corpus.
- Large active material is spread across `research/`, `benchmarks/`, `datasets/`,
  `foundry_datasets/`, `Downloads`, and `C:\tmp`.
- `C:\tmp` contains several old NEXUS worktrees/clones and diagnostic reports;
  these should not be moved wholesale until their branch and PR state is known.
- `Downloads\Papers` contains confidential scientific/red-team research PDFs and
  should remain ignored if copied into NEXUS.

## Proposed Buckets

| Bucket | Use |
| --- | --- |
| `docs/handoff/` | Agent handoff reports and PR evidence. |
| `docs/operations/` | Operator runbooks, worklogs, repeatable procedures. |
| `docs/reports/windows-resource-guard/` | Windows resource reports from `scripts/windows_streaming_resource_guard.ps1`. |
| `docs/research/mcp/` | MCP architecture logs, handoffs, and synthesis notes. |
| `docs/research/hf-rd/` | Hugging Face R&D plans and benchmark notes. |
| `docs/research/security/` | Red-team/security synthesis that is safe as text. |
| `docs/research/papers/` | Scientific PDFs; ignored by Git. |
| `benchmarks/` | Source code and small manifests for benchmark generation. |
| `datasets/` | Local generated datasets; ignored or staged only by explicit policy. |
| `MIXED/` | Uncertain files for manual review; ignored by Git. |

## Next Action Gate

Before moving files, complete PR #32 gate review:

- PR #32 head after env cleanup: `2a30061`
- Git mergeability: mergeable
- Blocking checks at this checkpoint: Vercel deployment blocked, Cloudflare Workers failed
- Decision: do not merge until deployment status is resolved or explicitly waived
