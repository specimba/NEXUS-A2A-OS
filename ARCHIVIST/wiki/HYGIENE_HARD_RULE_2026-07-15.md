# NEXUS Hygiene Hard Rule (2026-07-15)

## Scope (main 3 surfaces)
1. `C:\Users\speci.000\Downloads\NEXUSlogs`
2. `C:\Users\speci.000\Documents\NEXUS\ARCHIVIST`
3. `C:\Users\speci.000\Documents\NEXUS` (repo root)

## Rules
| Surface | Root may contain | Root must NOT contain |
|---------|------------------|------------------------|
| **NEXUSlogs** | `NEXUS*.txt`, optional `NEXUScontinuity_runs.jsonl`, intentional dirs (`hermes_*`, `_QUARANTINE_*`, `_runs`) | Loose `_grok_*.mjs`, `intern_*.png`, raw screenshots, one-shot scripts |
| **ARCHIVIST** | Curated dirs (`PAPERS`, `wiki`, dated reports) | Agent dump scripts, random JSON/PNG |
| **NEXUS** | Project source, `docs/`, `scripts/`, `tools/` | Throwaway `read_log*.py`, `run_it*.py`, accidental `nul` |

## Agent write paths (mandatory)
```
NEXUSlogs/_runs/<agent>/<YYYYMMDD>/
NEXUSlogs/NEXUS_<TOPIC>_<stamp>.txt          # human continuity only
Documents/NEXUS/ARCHIVIST/wiki/ or reports/  # durable notes
Documents/NEXUS/output/ or logs/             # generated artifacts
```

## Attribution (2026-07-15 NEXUSlogs mess)
- **Primary:** Grok CDP Intern session — `_grok_*`, `intern_drive_*`, `jupyter_*`, screenshots
- **Secondary:** Hermes/lane monitors — `a800_monitor*`, `lane_watch*`, `intern_workbench*`
- Quarantine: `Downloads\NEXUSlogs\_QUARANTINE_agent_droppings_*`

## CDP note
Chrome **Leave site?** / beforeunload freezes automation unless `Page.setIntercept*` / JS dialog accept is armed **before** reload. Prefer soft re-attach without refresh when possible.

## Status
- Enforced starting 2026-07-15 after Intern A100 dual-surface work.
- Zero-tolerance scatter at the three roots.
