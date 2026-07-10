# Intern-AI / Shanghai AI Lab workbench — continuity & cloud drive

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Operator points** | ~3690 remaining (probe snapshot) |
| **Cloud drive** | 0.6GB / **30GB** persistent under `/data` |
| **Primary use** | Fine-tunes, merges, dataset forge/test, vector/KV analysis — **not** Modal Image Weaver (keep Modal for NEXUS visual studio) |

## Surfaces

| Surface | URL pattern | Role |
|---------|-------------|------|
| Dev machine create | `https://d.intern-ai.org.cn/workbench/dev-machine/create` | Interactive GPU box (VS Code–like + Jupyter) |
| Discovery notebook job | `https://discovery.intern-ai.org.cn/org/ailab/job/...` | Offline notebook tasks (e.g. `NEXUS_scientist_v0.1`) |
| Platform nav | Research assistant · Thesis Space · **SCP Plaza** · Scientific data · Asset Space · **workbench** | Science + compute |
| Existing box | **NEXUS-GPU-test1** (`nb-2fc615787f57753dbe3fa2cbb094a9f2`) | A100×1 80Gi, **Stopped** ~10d — **start before new create** |

Max **10** dev machines. Prefer **restart NEXUS-GPU-test1** over spawning duplicates.

## Resource SKUs (operator-visible)

| SKU | GPU | Use when |
|-----|-----|----------|
| Nvidia A100-1-80G | A100×1 80Gi | Default NEXUS train/merge/bench (matches existing box) |
| Nvidia A100-8-80G | A100×8 | Multi-GPU merge / large DPO only if points budgeted |
| Ascend910B-1/8-64G | 910B | Ascend-native stacks only |
| CPU-4C-16G | none | Data prep / pack / non-GPU ETL |

Default bill snapshot: ~**11 points/hour**, 8h session ≈ **480 points** (dev machine) / **424** (training form). Prefer short runs + save to `/data`.

## Persistence rules (do not lose jobs)

| Path | Lifetime | Put here |
|------|----------|----------|
| **`/data`** (cloud drive) | Survives stop / release / delete of machine; shared across machines | Code exports, checkpoints, datasets, logs, `discovery-ctl` packs |
| **`/home/mw/project/`** (notebook) | Project workspace (preserved for that project) | Active notebooks, scripts |
| **`/home/mw/input/`** | Mounted datasets (hidden if none) | Read-only mounts (max 5 datasets) |
| **`temp` / machine-local non-`/data`** | **Wiped on release** | Scratch only |

### Cloud drive CLI (`discovery-ctl`)

```bash
# Upload local → cloud drive root (or subpath)
discovery-ctl clouddisk upload --local "./file1.txt,./file2.txt,folder1/" --remote-path /

# Download cloud → local
discovery-ctl clouddisk download --remote-path "/file1.txt,/folder1/" --output .

# Delete remote
discovery-ctl clouddisk delete --remote-path "/file1.txt"
```

**NEXUS convention on cloud drive:**

```
/data/NEXUS/
  repo_sync/          # git archive or sparse clone snapshots
  checkpoints/        # LoRA / merge outputs
  datasets/           # forged or sliced sets
  benches/            # eval JSONL + scores
  logs/               # training + TensorBoard exports
  kv_cache_studies/   # vector / K-V analysis artifacts
```

## Training tasks vs dev machines

| Mode | Source code | Startup | Persist results |
|------|-------------|---------|-----------------|
| **Dev machine** | Live VS Code/Jupyter | Interactive | Save to `/data` before stop |
| **Custom training** | Git repo **or** local upload **or** cloud drive | `/code/workspace` + command | `/data` + TensorBoard `TENSORBOARD_LOGDIR` |
| **Notebook offline** | Associated notebook | Image e.g. `Python3.12-cuda12.4-torch2.6.0` | `/home/mw/project` + cloud drive |

TensorBoard:

```python
from torch.utils.tensorboard import SummaryWriter
import os
writer = SummaryWriter(os.environ.get("TENSORBOARD_LOGDIR"))
```

## Dataset catalog (platform — sample high-value)

Prefer mounting **only what the job needs** (max 5):

| Dataset | Domain | Scale note |
|---------|--------|------------|
| ERA5 upper-air V5 | Earth Science | **231 TB** — do not mount whole; subset via platform tools |
| Sci-Base literature | Multi-science | MinerU deep parse |
| AFDB / SwissProt | Protein structures | Large; slice |
| AdaBrain-Bench | EEG / neuroscience | 1.28 TB |
| 3D Turbulence DNS | CFD | 1 GB class |
| ChemBench / CheMatAgent | Chemistry tools | Small, good for agent benches |
| Animal Kingdom / APT-36K | Behavior / pose | Mid |
| BOLD5000 / BraTS-2021 | fMRI / MRI | Medical |
| Cantor HEA / AirfRANS | Materials / aero | Generative/physics ML |

Also: operator-uploaded sets (`123`, `GemmaTest`, …) appear in mount picker.

## Recommended NEXUS job classes on Shanghai

1. **Local 8GB VRAM overflow** — anything that OOMs on home box (12B Q4 merges, long-context KV probes).
2. **DPO / GRPO phase-1** — guard reward models; judge = cloud (`deepseek-v4-pro`), train = A100 box.
3. **Abliteration / heretic merge experiments** — write weight deltas to `/data/NEXUS/checkpoints`.
4. **Dataset forge + bench** — security/guard JSONL, then eval on VibeThinker / Mythos / Gemma stacks.
5. **SCP-adjacent science agents** — use SCP Plaza tools + Intern Discovery bridge (`nexus_os/bridge/intern_discovery.py`) when trust ≥ gate.
6. **Not here:** NEXUS Image Weaver / NSFW studio → **Modal credits**.

## Resume checklist (every session)

1. Start **NEXUS-GPU-test1** (or create only if max-10 allows and box is dead).
2. `discovery-ctl clouddisk download` latest `/data/NEXUS/repo_sync` if machine is fresh.
3. `ls /data/NEXUS /home/mw/project /home/mw/input`
4. Confirm points balance; set runtime **≤8h** unless overnight intentional.
5. Before stop/release: push checkpoints + logs to `/data`, optional git remote push.
6. Log a row in `NEXUScontinuity_runs.jsonl`: `kind=intern_gpu_session`, machine id, points spent estimate, artifacts path.

## Related NEXUS code

- `nexus_os/bridge/intern_discovery.py` — JWT + SCP tool map  
- `docs/operations/INTERN_AI_PROVIDER_BOOT_2026-06-03.md`  
- Multi-lane doctrine: Intern lane = **primary free GPU lab** (prefer over GMI for heavy jobs)
