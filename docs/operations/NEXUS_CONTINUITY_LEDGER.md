# NEXUS Continuity Ledger

| Field | Value |
|-------|-------|
| **Canonical vault file** | `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl` |
| **Env override** | `NEXUS_CONTINUITY_LEDGER` |
| **Schema family** | `nexus.continuity.run.v1` (DirectorRunner) + lightweight preflight rows |

## What this file is

Append-only **JSON Lines** evidence of what the browser / agent automation layer just did:

- stack preflight (ready / blocked lanes)
- supervised send / wait / response cycles
- director actions (when Hermes / Browser-AI supervisor runs)

It is **not** the chat transcript itself. Chat text lives in the live browser tabs
(Grok / ChatGPT / …). The ledger is the **orchestration receipt book**.

## What each line means (preflight rows)

`lane_stack_preflight.mjs` appends compact rows:

| Field | Meaning |
|-------|---------|
| `ts` | UTC timestamp |
| `kind` | e.g. `lane_stack_preflight`, later `lane_send_proof` |
| `agent` | Who wrote the row (`grok-build-0.1`, `browser_ai_supervisor`, …) |
| `port` | CDP port (9224 = authenticated multi-lane Chrome) |
| `status` | `STACK_READY` / `STACK_PARTIAL` / `STACK_EMPTY` / send statuses |
| `ready_lanes` | Lanes that answered READY to a DOM probe |
| `absent_lanes` | Lanes with no matching tab |
| `blocked_lanes` | Lanes present but not automation-ready |
| `page_count` | Page targets on that CDP after the cycle |

## What DirectorRunner rows mean

When the full supervisor runs with `NEXUS_CONTINUITY_LEDGER` set, rows include:

| Field | Meaning |
|-------|---------|
| `run_id` | Unique run id |
| `agent_id` | `browser_ai_supervisor` |
| `source_lane` | Which AI source |
| `progress_class` | `NOOP_RECAP` / `ADVISORY_ONLY` / `EVIDENCE_DELTA` / `IMPLEMENTED_DELTA` / `VERIFIED_DELTA` |
| `input_fingerprint` / `output_fingerprint` | Hashes of visible surface before/after |
| `artifact_paths` | Files written this run |
| `provider_calls` | Provider traffic count |
| `blocker` | Why automation stopped (setup, auth, duplicate tab, …) |
| `next_action` | What the director recommends next |

## Silent preflight vs real conversation

| Command | Opens new Chrome? | Sends chat? | Where to see proof |
|---------|-------------------|-------------|--------------------|
| `lane_stack_preflight.mjs` | No (reuses :9224) | No | JSON stdout + ledger row |
| `lane_stack_preflight.mjs --observe` | No; dwells on each tab | No | Same Chrome window, tab focus |
| `send_grok_cdp.ps1 -PromptFile …` | No | **Yes** | Grok tab + wait JSON + probe tail + ledger |
| `run_browser_ai_supervisor.ps1` | No (may hide unless `VISIBLE_LANES=1`) | Via director policy | Director runtime + ledger |

## Hygiene

Old name `continuity_runs.jsonl` was renamed to **`NEXUScontinuity_runs.jsonl`**
so it matches the NEXUS* prefix convention in the vault root.
