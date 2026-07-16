# NEXUS Whole-System Deployment Guide

## Quick Start

```powershell
# One command to deploy everything
python scripts/deploy/deploy_all.py

# Or deploy specific waves
python scripts/deploy/deploy_all.py --wave 0  # Freeze + continuity
python scripts/deploy/deploy_all.py --wave 1  # Model control plane
python scripts/deploy/deploy_all.py --wave 2  # Protocol integration
```

## What Gets Deployed

### Wave 0 — Freeze Tree + Repair Continuity
- Generates dirty-tree ownership manifest
- Adds process locking + fsync + hash chaining to continuity
- Makes Downloads ledger canonical
- Verifies MiniMax license correction

### Wave 1 — Canonical Model Control Plane
- Removes synthetic 0.45 scores (replaced with null = UNSCORED)
- Adds missing aliases (GLM-5.2, Leanstral)
- Extends registry generator to emit npm sources/scores + Hermes + clients
- Builds Model Card v2 with all required fields

### Wave 2 — Protocol Integration
- Creates NexusExecutionEnvelope v2 schema
- Retires duplicate MCP on 7358
- Verifies 7354 as canonical MCP

### Supporting Modules
- `continuity_repair.py` — Ledger repair CLI (`nexusctl continuity repair`)
- `model_card_score_v2.py` — Registry migration to v2
- `benchmark_framework.py` — Frozen eval packs + edge-case stress tests
- `cli_consolidation.py` — Unified command registry

## Post-Deploy Checklist

1. Run `python scripts/deploy/deploy_all.py` (Wave 0-2)
2. Run `python scripts/ocr/ocr_client.py <screenshot.png> --mode struct` for OCR
3. Verify: `nexusctl ports doctor --band-only`
4. Verify: `nexusctl continuity status`
5. Start experiments: `python scripts/a800_run.py --template sera_v1`

## Architecture Reference

See `docs/plans/NEXUS_CODEX_GPT56_SOL_ULTIMATE_GROUNDING_AND_MASTER_PLAN_2026-07-10.md` for the full reference.
