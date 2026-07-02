# Zo computer browser collaboration with NEXUS (A2A lane)

**Goal:** Second cloud computer (Zo) with browser + frontier models collaborates with Windows NEXUS like Grok CDP — structured handoffs, not ad-hoc chat.

## Topology

| Role | Host | Transport | Models |
|------|------|-----------|--------|
| Grok planner | Windows Chrome :9224 | Node CDP + director | Grok 4.x Expert (browser) |
| Hermes executor | WSL / local | ModelRelay :7350 | auto-fastest / OAuth |
| Zo researcher | Linux cloud | agent-browser / Playwright | Provider free frontier tiers |
| Governance | Windows | Grok MCP :7354 | Tool allowlist + audit |

Zo does **not** replace Grok lane; it is a **parallel cloud lab** for hosting experiments, wide egress tests, and multi-model bBoN rollouts Hermes judges locally.

## Connecting Zo to NEXUS Grok session (optional)

When operator approves tunnel:

```bash
# On Zo (example)
agent-browser connect http://<WINDOWS_HOST>:9224
# or Playwright:
# chromium.connectOverCDP('http://127.0.0.1:9224')  # via SSH -L 9224:127.0.0.1:9224
```

**Windows side:** keep Chrome **visible** (default `start_grok_cdp_9224.ps1`); restore UI:

```powershell
node tools\browser_ai_supervisor\grok_cdp_restore_window.mjs --port 9224 --mode maximized
```

**Never** default to `-SilentBackground` for operator Grok work.

## A2A message contract (same as director memory)

Use schema `nexus.browser_ai.supervisor.memory.v1` fields:

- `source_id`: `grok-project-nexus` | `zo-browser-lab`
- `visible_fingerprint`: sha256 of probe excerpt
- `action`: CONTINUE_SENT | ARTIFACT_CAPTURED | RETRY_LATER
- `behavior_narrative`: optional bBoN summary (see skill `nexus-bbon`)

**Football pass:**

1. **Grok (browser)** emits `[GROK-PLAN]` bullets + optional file paths under `Downloads/ARCHIVIST`.
2. **Hermes** verifies paths, runs tests, implements only bounded slices; replies with `[HERMES-EXEC]` evidence (command output, commit SHA).
3. **Zo** runs cloud-only tasks (deploy sketch, API probe, parallel model rollouts); returns narratives to ARCHIVIST; Hermes **judge** picks one.

## Zo-only workloads (keep off Windows GPU)

- Hosted service smoke tests
- Multi-model bBoN via `/zo/ask` parallel sessions
- Playwright DOM recipes exported as skills (not pixel agents)
- Checkpoint: `.z_checkpoint.json` on Zo; NEXUS uses `scratch/browser_ai_mcp_runtime/`

## Security

- Tunnel CDP only with explicit operator approval; localhost bind on Windows.
- No credentials in pasted prompts; burned one-time secrets are discarded.

## Related docs

- `NEXUS_CDP_ZO_AGENT_S_MUTATION_2026-07-02.md`
- `GROK_CDP_DIRECTOR_RUNBOOK_2026-06-21.md`
- `HERMES_GROK_CDP_DUAL_LANE_2026-06-30.md`