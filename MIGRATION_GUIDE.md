# Migration Guide: Experimental → v3.0 (m3-hardened)

## Overview
This guide maps legacy experimental folders to the new canonical v3.0 architecture.

## Critical Preservation: cloud_pack
The `cloud_pack` directory contains optimized agent logic (`2_NEXUS_SOURCE.txt`) designed for <1k token usage.
- **Status**: PRESERVED & INTEGRATED
- **Usage**: Reference `2_NEXUS_SOURCE.txt` for efficient agent prompting patterns.
- **Integration**: These patterns are now validated by the C5 Gate test suite.

## Mapping Table

| Legacy Folder/File | New Canonical Location | Action |
|---|---|---|
| `cloud_pack/2_NEXUS_SOURCE.txt` | `cloud_pack/2_NEXUS_SOURCE.txt` | **KEEP** (Source of Truth for Agents) |
| `GLM-5-Turbo-backend-SWARM` | `src/nexus_os/engine/` | Archive experimental, use Hermes |
| `NEXUSCLOUDSTARTER` | `00_QUICKSTART.md` | Superseded by Quick Start |
| `skills/` | `src/nexus_os/engine/hermes.py` | Migrated to Skill Adapter |
| `cron/` | `tests/cron/` | Tests preserved, logic in `src/` |
| `MISSION_REPORT.txt` | `EVIDENCE.md` | Auto-generated per C5 Gate run |
| `COLD_HANDOFF.txt` | `04_GOVERNANCE.md` | Invariants formalized |
| `GIT_WORKFLOW.txt` | `GIT_WORKFLOW.txt` | Updated for v3.0 tags |
| `AGENT_WORKSPACES.txt` | `AGENTS.md` | Updated protocol |

## Verification Steps
1. Run `python scripts/c5_integration_gate.py`
2. Verify `EVIDENCE.md` shows [PASSED]
3. Check `cloud_pack/VALIDATION.txt` against new metrics

## Deprecation Notice
- Old experimental branches (`codex/experimental`, etc.) are archived.
- `main` branch is now the single source of truth.
- Tag `m3-hardened` marks the stable baseline.
