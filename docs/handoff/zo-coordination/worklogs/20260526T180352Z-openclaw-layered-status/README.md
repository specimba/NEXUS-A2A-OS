# OpenClaw Layered Status Bundle — 2026-05-26 18:03 UTC

Generated under the bounded execution slice in
`ZO_OPENCLAW_NEXT_SAFE_SLICE_2026-05-26`.

## Contents

| File | Phase | Purpose |
|---|---|---|
| `openclaw_status_deep.txt` | A | Redacted `openclaw status --deep` |
| `openclaw_security_audit_deep.txt` | A | Redacted security audit |
| `openclaw_agent_list.txt` | A | Redacted agent list |
| `tailscale_serve_status.txt` | A | Tailscale Serve target |
| `ss_listening_ports.txt` | A | Filtered listening sockets |
| `provider_mapping_redacted.txt` | A | Provider/model map with no keys |
| `bind_address_analysis.txt` | A.1 | Answer to the `0.0.0.0:18789` exposure question |
| `token_hygiene_plan.md` | B | Token inventory + proposed rotation order (no execution) |
| `provider_smoke_result.md` | C | One agent-runtime smoke + diagnosis |

## Phase D drafts (separate path)

`docs/handoff/zo-coordination/installers/`
- `openclaw_install.sh` — pre-paired installer (DRAFT)
- `openclaw_migrate.py` — v3→v4 config migration shim (DRAFT, dry-run verified)
- `redaction_filter.py` — secret stripper (DRAFT, 10/10 selftests pass)

## Headline results

- **Bind contradiction resolved**: gateway binds `0.0.0.0:18789`. External reach is gated
  by Modal sandbox + tailscaled, not by the bind. Hardening proposal: bind `127.0.0.1` explicitly.
- **Provider routing smoke: FAILED** (as predicted). Agent default targets `openai/gpt-5.5`,
  no OpenAI key configured. NIM/KiloCode/OpenRouter providers are configured at the provider
  layer but not registered as models for the `main` agent.
- **Token hygiene**: inventory complete, rotation NOT executed. Operator approval required.
- **Installer drafts**: redaction_filter selftest passes 10/10; migrate dry-run is clean.

## Hard boundaries observed

- No tokens, keys, or pairing IDs in any output (leak-check passed).
- No re-enable of `telegram-claw-gateway`.
- No edits to `paired.json`.
- No force-push.
- No broad service restart.
- No claim of swarm-readiness.
