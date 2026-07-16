# NEXUS Repo Reorganization Plan — 2026-07-13

## Current State

- Repository: `https://github.com/specimba/NEXUS_discovery_GPU`
- HEAD: commit ~1,678 on `main`
- Folders: `docs/`, `reports/`, `scripts/`
- Branches: Multiple divergent branches from multi-agent work

## Target Branch Structure

```
main                    ← Clean, tested, proven commits only
├── session4/a800/      ← A800 training (auto-pushed by calm loop)
├── experiments/
│   ├── sera/           ← Soft-verified SFT (PAPERS P0a)
│   ├── rift/           ← Trust-weighted loss (PAPERS P0b)
│   ├── fugu/           ← Soft-target SFT (PAPERS P0c)
│   ├── cleaner/        ← Trajectory purification (PAPERS P0d)
│   ├── ftp0/           ← Final-token preference (PAPERS P0f)
│   ├── arena-v2/       ← Scoring + shadow arena (PAPERS P0g)
│   └── guard-dpo/      ← Guard preference optimization
├── datasets/
│   ├── benchmarks/     ← Guard eval suites (from D:\NEXUS_COLD)
│   ├── sft-seeds/      ← SFT training data (from D:\NEXUS_MODELS)
│   └── merges/         ← Merge manifests
├── docs/
│   ├── PAPERS_DISTILLATION.md
│   ├── A800_RUNBOOK.md
│   ├── CDP_AUTOMATION.md
│   └── OCR_PIPELINE.md
└── scripts/
    ├── stress/         ← Guard stress test framework
    ├── ocr/            ← OCR pipeline (PaddleOCR service)
    ├── monitor/        ← Lightweight monitoring (no AI context burn)
    └── training/       ← Training job scripts
```

## Execution Steps

### Phase 1 — Stabilize Current Work
1. Tag current `main` as `pre-reorg-YYYYMMDD`
2. Merge all uncommitted working-tree changes to `main`
3. Push to remote: `git push origin main --force-with-lease`

### Phase 2 — Create Branch Structure
```bash
# Create from current main
git checkout -b session4/a800 main
git checkout -b experiments/sera main
git checkout -b experiments/rift main
git checkout -b experiments/fugu main
git checkout -b experiments/cleaner main
git checkout -b experiments/ftp0 main
git checkout -b experiments/arena-v2 main
git checkout -b experiments/guard-dpo main
```

### Phase 3 — Restructure Directories
```bash
mkdir -p datasets/benchmarks datasets/sft-seeds datasets/merges
mkdir -p scripts/stress scripts/ocr scripts/monitor scripts/training
# Move existing content into new structure
git mv docs/research/PAPERS_MASTER_DISTILLATION.md docs/
git mv scripts/nexus_cloud_suite/* scripts/training/
```

### Phase 4 — Dataset Sync
```bash
# Push D: drive assets to repo (LFS for large files)
git lfs track "*.pt" "*.gguf" "*.safetensors" "*.bin"
rsync -av D:/NEXUS_MODELS/datasets/ datasets/sft-seeds/
rsync -av D:/NEXUS_COLD/level5_migrations_20260605/NEXUS/datasets/bench_*.json datasets/benchmarks/
```

### Phase 5 — Clean Up
```bash
# Remove duplicate registries
rm -f nexus_os/relay/config.ts  # superseded by config/generated.ts
rm -f nexus_os/gmr/chimera_router.py  # superseded by chimera_router_v2.py

# Remove ARCHIVISTAudit-ledger duplicates
rm -f knowledge.md  # superseded by 01_PROJECT_STATE.md
```

## Commit Discipline

- No `git add .` — always explicit file lists
- Commit messages: `[AREA] verb + object + proof`
- Max 1 behavior change per commit
- Every commit must pass `gen_model_registry.py --check`

## Backup & Rollback

- Tag before every destructive op
- `git reflog` is the safety net
- `D:\NEXUS_COLD` is the air-gapped backup
