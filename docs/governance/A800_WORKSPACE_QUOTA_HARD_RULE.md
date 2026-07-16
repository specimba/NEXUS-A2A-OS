# A800 Workspace Quota — HARD RULE (consciousness point)

**ID:** `A800-HR-001`  
**Status:** HARD RULE — non-negotiable for Intern-Discovery / A800 agents  
**Incident:** 2026-07-11 Project 101%→120% blocked all writes; multi-notebook thrash amplified damage  
**Recovery:** Project cleaned to ~14%; single notebook `Notebook-python3-2306`; train tick 19 resumed  

---

## One-line rule

> **Never treat A800 as “GPU free → pull anything.” Treat `/home/mw/project` Project % as a hard capacity gate equal to CUDA.**

---

## Facts agents must keep conscious

| Meter | Meaning | Agent action |
|--------|---------|----------------|
| **DISK** (~30%) | Machine system volume | Informational only |
| **PROJECT** | **Workspace quota on `/home/mw/project`** | **HARD GATE** |
| **WORK** | Ephemeral work dir | Prefer temp writes here if allowed; not durable |
| **GPU / Remaining Duration** | Compute time left | Independent of Project % |

Platform warning (authoritative):

> Workspace is full → system use is limited → clean **`/project`** **or** contact admin to increase workspace space.

**Project % ≠ Disk %.** Disk can be fine while Project is 120% and nothing can write.

---

## HARD RULES (must follow)

### HR-1 — Preflight before any data gravity / Hub download
- Measure project usage **before** `snapshot_download` / multi-pack pulls.
- **If Project ≥ 80%:** no new large packs. Train-only or jewel-inventory only.
- **If Project ≥ 90%:** **STOP all downloads.** Cleanup only. Report GH `mode: quota_block`.
- **If Project ≥ 100%:** **STOP all non-cleanup cells.** Free space or escalate admin. Do not “retry pull.”

### HR-2 — Size-aware pulls (smarter data)
- Prefer **already-on-disk** datasets under `NEXUS_session4/datasets/`.
- Prefer **small jewels** (ToolACE, xlam-irrelevance, Salesforce xlam) over multi‑hundred‑MB TokenHD packs until quota headroom ≥ 30%.
- One pack at a time when Project > 50%. Cap concurrent Hub workers.
- Never start Toucan-scale / multi‑GB packs without explicit user OK **and** Project < 40%.

### HR-3 — Single notebook kernel only
- **Exactly one** live `Notebook-python3-*` for automation.
- **Do not** open extra notebooks when ensure fails; fix the existing tab.
- On status page: shut every kernel except the designated one (default keep: latest proven, e.g. `2306`).
- Multi-kernel mess → thrash + partial downloads + quota climb. Treat as incident.

### HR-4 — No idle on 启动页
- Inter-tick sleep must **not** leave the agent “waiting” on launcher UI as if work is progressing.
- Prefer short phase gaps (e.g. 180s) over 900s splash parking.
- After sleep: ensure notebook tab, not 启动页, before fill/run.

### HR-5 — Cleanup is first-class work
- When Project ≥ 80%, cleanup is the task — not optional.
- Safe delete order: caches → incomplete → old tinylm ckpts → failed packs → **only then** reconsider jewels.
- Keep list (unless user overrides): ToolACE, xlam-irrelevance, Salesforce xlam.
- Prefer shell `!rm` / Terminal if notebook kernel is wedged by over-quota.

### HR-6 — Quota increase is admin-side
- There is **no** reliable public self-serve “expand Project” for org-usage machines (`labelUsageType=ORGUSAGE`).
- Self-serve path: clean `/project`.
- Expand path: org admin / platform support (“工作区存储配额 / project 磁盘”).
- GPU time renew ≠ Project expand.

### HR-7 — Proof still required
- GH reports must include project usage when possible (`project_used_mb`, `project_note`).
- Do not claim “data downloading” when Project is blocked.
- Do not claim “waiting on notebook” when actually sleeping or on 启动页.

---

## Operating checklist (every A800 session)

1. [ ] Project % from status bar (or after cell: estimate du of `/home/mw/project`)
2. [ ] Kernel list: **one** Notebook-python3 only
3. [ ] Tab: notebook, not 启动页
4. [ ] Mode: train if Project high; data only if Project < 80% and size-capped
5. [ ] After data tick: re-check Project %; cleanup if jumped > 15 points
6. [ ] GH proof uploaded before long sleep

---

## Smarter defaults (policy)

| Situation | Default |
|-----------|---------|
| Project < 50% | Normal train + small data packs |
| Project 50–80% | Train primary; data = single small pack or inventory |
| Project 80–100% | Train-only **or** cleanup; no Hub multi-pack |
| Project ≥ 100% | Cleanup / admin only |
| Multi kernels | Kill extras before any tick |
| After refresh / intro bug | ensure one nb → check Project → then tick |

---

## Related paths

- Project root: `/home/mw/project`
- Session tree: `/home/mw/project/NEXUS_session4/`
- Datasets: `.../datasets/{tokenhd,tool}/`
- Drivers: `cdp_agent_scratch/intern_cdp/intern_s4_a800_go.mjs`, `_a800_bang_rm.mjs`
- GH proof: `specimba/NEXUS_discovery_GPU` `reports/session4/a800/`

---

## Consciousness prompt (paste into agent context)

```
A800-HR-001: Project workspace quota is a hard gate.
DISK free ≠ PROJECT free. Before any Hub download or multi-pack data tick:
check Project %. ≥80% → no large pulls. ≥90% → stop downloads. ≥100% → cleanup only.
One Notebook-python3 kernel only. Never thrash 启动页. Prefer small jewels + train
over filling /project. Work smarter: capacity-aware, not GPU-only.
```

---

## Smart workarounds (do not get stunned)

Incident lesson 2026-07-11: data tick `pull_ok:9` refilled Project to **112%** after cleanup because the conveyor still used **old multi-pack defaults**.

### W-1 — Train-primary default
- `A800_DATA_EVERY` default **0** (train only).
- Enable data ticks only when Project **< 50%** and user wants labels, with jewel-first packs.
- GPU proof does not require filling Project.

### W-2 — Never re-download what is on disk
- If `datasets/{kind}/{repo__}` already has ≥3 files and >100KB → **CACHED**, skip Hub.
- Stops thrash re-pull that re-blows quota with the same packs.

### W-3 — Mid-loop quota stop
- After each pack, re-measure Project used MB.
- If est ≥ 80% → **stop remaining packs** immediately (`quota_stop_mid`).

### W-4 — Jewel-first pack ladder
| Project est | Packs |
|-------------|--------|
| ≥ 90% | none (quota_block) |
| 50–90% | ToolACE + xlam-irrelevance + Salesforce only (+ optional tiny label) |
| < 50% | full small ladder allowed, still max one oversize warning |

### W-5 — WORK / TEMP paths (when Project tight)
- Prefer ephemeral `/home/mw/temp` or `/home/mw/work` for experiments if platform WORK % stays low.
- Durable training data only in `/project` when Project headroom exists.
- Never assume WORK is unlimited — re-check meters.

### W-6 — Use on-disk inventory as data mode
- When Project high: data tick = **list + hash + GH report** of existing `datasets/`, not Hub.
- Training can read local ToolACE / xlam without new pulls.

### W-7 — Cleanup is automated first response
- Tools: `_a800_bang_rm.mjs` (shell magics).
- Keep jewels; drop tokenhd multi-pack / incomplete / caches / tinylm ckpts.
- Do this **before** relaunch if Project ≥ 90%.

### W-8 — Single kernel + short phase
- One `Notebook-python3-*`. Phase sleep **180s** default.
- No multi-kernel spawn; no 15‑min splash park.

### W-9 — Driver reload after rule change
- Long-running `node intern_s4_a800_go.mjs` keeps **old code** until killed/relaunched.
- After patching HR-001: **restart conveyor** or next data tick still uses stale multi-pack list.

### W-10 — Admin expand only if cleanup is not enough
- Org usage machines: ask admin for 工作区/project disk expand.
- GPU remaining-time renew does **not** raise Project.
