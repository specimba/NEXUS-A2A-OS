# Nexus OS Lane Registry

## Lane Types
| Prefix | Purpose | Surface |
|--------|---------|---------|
| OPS | Operations | Path truth / trust state / next order |
| GOV | Governance | Contract truth only |
| BLD | Build | One bounded surface patch |
| VAL | Validate | Read-only audit |
| PRM | Promotion | Merge / carry-forward review |
| EXP | Explore | Scratch, no production authority |

## Active Lanes
*None yet — register lanes here as they are created.*

## Rules
- One lane = one purpose
- One lane = one execution surface
- Lane ID block is authority, title is cosmetic
- Scratch `task.md`/`implementation_plan.md`/`walkthrough.md` are never authoritative
- Trust raw terminal output over summaries
