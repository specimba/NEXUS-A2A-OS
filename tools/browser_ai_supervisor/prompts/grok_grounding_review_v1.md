You are reviewing the NEXUS Continuous Grounding and Browser-AI Control implementation as a collaborating architecture/security agent.

Current verified local contract:
- Append-only JSONL is authoritative; SQLite uses rollback-journal mode as a rebuildable single-writer index.
- Sources are ARCHIVIST, NEXUSlogs, PAPERS, and the NEXUS repository.
- Native filesystem events debounce for 30 seconds; an hourly full reconciliation recovers missed/overflowed events.
- Source cards fail closed at E0 when body extraction fails. Only E1+ cards can enter reviewed promotion proposals.
- Canonical project-state and architecture documents never mutate automatically.
- Isolated Grok CDP is port 9224 with a non-default Chrome profile; MCP bridge is 7354; Brain API 7352 is reserved.
- Unchanged fingerprints, setup blockers, and cooldowns cause zero provider calls.

Produce one versioned artifact named `NEXUS_GROUNDING_BROWSER_CONTROL_REVIEW_v1.md`. Review exactly:
1. GroundingEvent schema completeness, event lineage, deletion/rename semantics, crash consistency, and JSONL-to-SQLite rebuild behavior.
2. Source-card promotion gates, contradiction handling, extraction-failure behavior, secret/browser-store exclusions, and evidence grading.
3. CDP logon recovery, single-instance behavior, duplicate-tab risk, bounded retries, authentication/setup blockers, and no-op/provider-call rules.
4. ReadDirectoryChangesW/watchdog overflow recovery and the hourly reconciliation contract.
5. Integration boundaries for NEXUSCLAW 8-channel memory and durable ARCHIVIST handoff.

For each finding include severity, exact failure mode, minimal fix, and deterministic test. End with:
- a proposed schema delta,
- a prioritized P0/P1/P2 patch list,
- an explicit list of claims you could not verify from this sandbox.

Do not claim local files were modified. Do not request secrets. Do not run destructive operations. Use MCP internet hands only for primary documentation if needed, and cite those sources in the artifact.
