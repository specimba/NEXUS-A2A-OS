# Intern workbench CDP automation plan

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Driver** | Chrome CDP `:9224` (same stack as multi-lane A2A) |
| **Tool** | `tools/browser_ai_supervisor/intern_workbench_cdp.mjs` |
| **Machine** | `NEXUS-GPU-test1` (`nb-2fc615787f57753dbe3fa2cbb094a9f2`) |
| **Ledger** | `NEXUScontinuity_runs.jsonl` kind=`intern_cdp_*` |

## Why CDP (not only operator clicks)

Intern is a **browser surface** like Qwen/GLM. Grok Build + multi-lane stack already own CDP. Manual “short path” is the fallback; **primary path** = probe → start → enter → (best-effort) smoke with operator only for auth/captcha.

## Surfaces (priority order)

| Priority | URL | Action |
|----------|-----|--------|
| 1 | `https://d.intern-ai.org.cn/workbench` | Machine list / start / enter |
| 2 | `https://d.intern-ai.org.cn/workbench/dev-machine/...` | Machine detail |
| 3 | VS Code–like web IDE after Enter | Terminal smoke |
| 4 | `https://discovery.intern-ai.org.cn/notebooks/run/...` | Notebook path (existing NEXUS_scientist_v0.1 tab) |
| avoid | Full ERA5 mounts, create new machine if test1 exists | Points waste |

## Phases

### Phase 0 — Presence & map (safe, default)
1. Find or open tab matching `d.intern-ai.org.cn` / `discovery.intern-ai.org.cn`.
2. `Target.activateTarget` + optional navigate to workbench root.
3. DOM inventory: buttons/links with text Start / 启动 / Enter / NEXUS-GPU / Stopped / Running.
4. Emit JSON map to `NEXUSlogs/intern_workbench_dom_map.json`.
5. **No start** unless `--start`.

### Phase 1 — Start machine (`--start`)
1. Locate card/row containing `NEXUS-GPU-test1` or notebook id fragment `nb-2fc615` / `2fc615787f57753d`.
2. Click control matching `/start|启动|start up/i` on that card.
3. Poll status text for Running / 运行中 (timeout default 180s).
4. Continuity: `intern_cdp_start`.

### Phase 2 — Enter IDE (`--enter`)
1. Click Enter / 进入 / Open.
2. Wait for IDE chrome (Activity Bar, terminal, or code-server markers).
3. Continuity: `intern_cdp_enter`.

### Phase 3 — Smoke (`--smoke`)
Best-effort only (VS Code web terminals vary):
1. Prefer: open terminal via keybinding (`Control+`` `) or menu.
2. Inject smoke script via clipboard + Enter, or `Runtime.evaluate` if terminal textarea accessible.
3. Smoke body (canonical):

```bash
mkdir -p /data/NEXUS/{repo_sync,checkpoints,datasets,benches,logs,kv_cache_studies}
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None); open('/data/NEXUS/logs/smoke_gpu.txt','w').write('ok\\n')"
```

4. If terminal not automatable: leave smoke commands in clipboard + `status=SMOKE_MANUAL` and notify operator once.
5. Continuity: `intern_cdp_smoke`.

### Phase 4 — Stop (`--stop`) — points hygiene
1. From workbench list, Stop when idle after smoke.
2. Never “release/delete” automatically.

## Hardening (match multi-lane denylist spirit)

- **Do not** `Target.createTarget` for random tabs if a workbench tab exists (reuse).
- **Do not** close Chrome / other lanes.
- **Do not** auto-create new GPU machines if a usable machine exists.
- **Do not run two GPUs at once** (points waste). Prefer **one** running machine (test2 primary).
- **Do not** mount datasets automatically (ERA5 risk).
- Login/SSO/captcha → `status=AUTH_REQUIRED` + stop.
- IDE smoke: prefer top-level `discovery-notebook-p.../code/` navigation; see `INTERN_CODE_SERVER_CDP_MAP.md`.

## Operator + agent split

| Actor | Role |
|-------|------|
| **CDP controller** | Navigate, map, start, enter, try smoke, stop |
| **Operator** | Login once, approve unexpected spend, captcha |
| **Codex/SOL** | Post-smoke train jobs using `/data/NEXUS` once smoke proves GPU |
| **Grok** | Own controller code + multi-lane doctrine wire |

## Live finding 2026-07-10 (first CDP map)

- Navigated `https://d.intern-ai.org.cn/workbench/dev-machine` successfully (L0).
- UI Chinese: 我的开发机 / 进入开发机 / 资源监控 / 算力余额 **3690**.
- **共 0 个** — machine list **empty**. Skeleton cards (`_cardSkeleton_*`, text `未知 GPU`) only; **Enter disabled** (`_disabled_*`).
- **NEXUS-GPU-test1 is not present** (released/expired/other org). Cannot Start until recreated.
- Selectors captured for real cards: `[class*='devMachineCard']`, `button[class*='enterBtn']`, `button[class*='actionBtn']`.

### Empty-list branch

1. `--phase map` → `MAP_OK_EMPTY_LIST` (exit 6).
2. Recreate: operator UI **or** `node ... --phase create` (maps form) then `--phase create --confirm` (spends points — gated).
3. Prefer SKU **Nvidia A100-1-80G**, name `NEXUS-GPU-test1`, short runtime.
4. Re-run `--phase start` / `--phase all`.

## Success criteria

| Level | Meaning |
|-------|---------|
| L0 | Workbench tab active + DOM map written |
| L0b | Machine list non-empty + target card visible |
| L1 | Start clicked + status Running |
| L2 | IDE entered |
| L3 | `/data/NEXUS/logs/smoke_gpu.txt` confirmed (or SMOKE_MANUAL with command ready) |

## Commands

```powershell
cd C:\Users\speci.000\Documents\NEXUS
# Map only (safe)
node tools\browser_ai_supervisor\intern_workbench_cdp.mjs --port 9224 --phase map

# Start NEXUS-GPU-test1
node tools\browser_ai_supervisor\intern_workbench_cdp.mjs --port 9224 --phase start --machine NEXUS-GPU-test1

# Full pipeline (map→start→enter→smoke attempt)
node tools\browser_ai_supervisor\intern_workbench_cdp.mjs --port 9224 --phase all --machine NEXUS-GPU-test1
```

## Related

- `docs/operations/INTERN_AI_SHANGHAI_WORKBENCH_CONTINUITY.md`
- `docs/operations/NEXUS_MULTI_LANE_A2A_DOCTRINE.md` (Intern = primary free GPU lab)
- Continuity ledger + Grok MCP `cdp_window_probe` for post-checks
