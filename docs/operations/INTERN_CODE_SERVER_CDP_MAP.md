# Intern test2 code-server CDP map (2026-07-10)

## Policy (hard)

- **One GPU at a time.** Never start test1 while test2 is running (points burn; no parallel benefit for smoke).
- Primary machine: **NEXUS-GPU-test2** `nb-582b5f51afb6b085773ce464c2654850`.
- Stop extras when idle.

## URL stack

| Layer | URL |
|-------|-----|
| Workbench list | `https://d.intern-ai.org.cn/workbench/dev-machine` |
| Shell (monitor chrome) | `https://d.intern-ai.org.cn/workbench/dev-machine/inside/55/nb-582b5f51afb6b085773ce464c2654850` |
| **code-server (real IDE)** | `https://discovery-notebook-p.intern-ai.org.cn/notebook/60400422/nb-582b5f51afb6b085773ce464c2654850/code/` |

Shell embeds code-server as **cross-origin iframe** (`iframe._iframe_na4i2_102`). Outer page only shows CPU/GPU monitors.  
**CDP rule:** navigate top-level to the **code/** URL (or attach OOPIF if available). Do not expect Monaco on the shell host.

## Confirmed UI (screenshot + live CDP)

- VS Code / code-server Welcome, folder `/root` (`.bashrc`, `.profile` in EXPLORER).
- **KILO CODE** sidebar + Chat (operator-installed; live HTML confirms kilo).
- Cline family present in extension marketplace assets (ARCHIVIST dump); use Kilo as primary agent pane for now.
- Integrated terminal **exists** in DOM (`.integrated-terminal`, `textarea.xterm-helper-textarea`, New Terminal `Ctrl+Shift+C`) but panel often **collapsed / off-viewport** under automated Chrome window metrics.
- Keyboard layout: **Turkish Q** — backtick terminal shortcuts unreliable; prefer palette / aria buttons / human click.

## ARCHIVIST sources

- `Downloads/ARCHIVIST/DinternVSCODEdevbrowserALLpositions.md` (Lighthouse-heavy; confirms inside URL + extension loads)
- `Downloads/ARCHIVIST/d.intern-ai.org.cn-20260710T085034.json`

## Smoke (manual once if CDP panel stuck)

In IDE terminal (click **Terminal** panel or **New Terminal** +):

```bash
mkdir -p /data/NEXUS/{repo_sync,checkpoints,datasets,benches,logs,kv_cache_studies}
nvidia-smi
python3 -c "import torch; print('cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None); open('/data/NEXUS/logs/smoke_gpu.txt','w').write('ok\n')"
ls -la /data/NEXUS/logs/; cat /data/NEXUS/logs/smoke_gpu.txt
```

Or ask **Kilo Code** (HY3 / DeepSeek V4) to run the same block and paste output.

## CDP automation status

| Capability | Status |
|------------|--------|
| List machines / start / enter | Works (list UI) |
| Open shell inside URL | Works |
| Top-level code-server navigation | Works (`hasMonaco`, **kilo:true**) |
| Terminal smoke via CDP Input | **Blocked** when panel off-viewport in automation window |
| Dual-GPU start | **Forbidden** going forward |

## Next code fix

`intern_workbench_cdp.mjs`:

1. Default machine = test2 only.  
2. Phase `ide`: open code/ URL top-level.  
3. Phase `smoke`: Emulation 1920×1080 + Ctrl+J + click `[aria-label*="New Terminal"]` + focus helper.  
4. Never start second machine if one is `运行中`.
