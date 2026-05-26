# Token Hygiene Plan — 2026-05-26

Status: INVENTORY ONLY. No rotation performed. Operator approval required before any rotation step.

## Active token classes

| Class | Location | Public-transcript exposure | Rotation impact |
|---|---|---|---|
| **OpenClaw gateway auth token** | `/root/.openclaw/openclaw.json` → `gateway.auth.token` | ⚠️ visible in prior chat transcript (string starting `35ce2a4a`) | dashboard + CLI must re-auth; ~2 min downtime |
| **OpenClaw gateway remote token** | same file → `gateway.remote.token` | same value as above, same exposure | covered by same rotation |
| **OpenClaw operator device tokens** | `/root/.openclaw/devices/paired.json` (mode 600) | not directly leaked; one entry was added via direct JSON edit, label = BREAK-GLASS | re-pair required after rotation; needs installer |
| **NVIDIA NIM API key (key 2)** | `/root/.openclaw/agents/main/agent/auth-profiles.json` (mode 600) + env var `NVDIA_NIM_KEY2` | not leaked | re-issue from NVIDIA console; ModelRelay + OpenClaw must pick up new env |
| **NVIDIA NIM API key (key 1, legacy)** | env var `NVIDIA_NIM` | not leaked | revoke at NVIDIA console; ensure nothing still reads it |
| **OpenRouter key (funded slot)** | env var `OPENROUTER_API_KEY` | partial prefix `sk-or-v1-64259…` appeared in transcript | currently 402 anyway; rotate at OpenRouter then re-fund or retire |
| **OpenRouter key (unfunded legacy)** | env var `OPENROUTER3_KEY` | prefix `sk-or-v1-d27db…` appeared in transcript | retire; do not re-fund |
| **KiloCode JWT** | env var `KILOCODE_API_KEY` | not leaked | re-issue from kilo.ai dashboard |
| **OpenCode Zen key** | env var `OPENCODE_ZEN_KEY` | not leaked | re-issue if endpoint becomes useful |
| **AutoClaw Telegram bot token** | svc env `AUTOCLAW_BOT_TOKEN` | ⚠️ value `8699842897:AAG6DSU-…` is in service config and partially visible in earlier service-listing output | rotate via @BotFather; bridge stays disabled |
| **KiloClaw Telegram bot token** | svc env `KILOCLAW_BOT_TOKEN` | partially visible in service listing | rotate via @BotFather |
| **Slack bot token** | svc env `SLACK_BOT_TOKEN` (`xoxb-…`) | partially visible in service listing | regenerate in Slack app config; bridge stays disabled |
| **GitHub token** | gh CLI keyring | not leaked | rotate only on schedule |
| **Confluent Kafka key** | svc `nexus-kafka-bridge` env | partially visible | rotate via Confluent console |

## Proposed rotation order (no execution yet)

1. **OpenClaw gateway tokens** (auth + remote) — highest urgency, leaked.
   - Pre-req: pre-paired installer script (Phase D) so we don't deadlock on circular approval again.
   - Window: ~5 min downtime for dashboard + CLI.
2. **OpenRouter funded key** — leaked prefix, useless anyway (402). Rotate or retire.
3. **Telegram bot tokens (AutoClaw + KiloClaw)** — leaked in service config. Bridge is disabled so rotation has zero blast radius.
4. **Slack bot token** — leaked in service config; rotate before bridge re-enable is even discussed.
5. **NVIDIA NIM keys** — not leaked, lowest urgency, but rotate alongside #1 if doing a clean baseline.
6. **OpenRouter unfunded legacy key** — retire entirely, do not rotate.

## Hard rules

- No token values in this document or in any future report.
- No rotation without operator approval per class.
- After rotation: update `auth-profiles.json` (mode 600), env vars, and service definitions atomically; do not commit those files.
- Rotation should always be followed by: redacted post-rotation status report → updated `paired.json` via installer (not manual edit) → smoke test.

## What I will NOT do

- Rotate any token without explicit operator approval.
- Print token values, prefixes longer than 8 chars, or suffix bytes.
- Re-enable `telegram-claw-gateway` as part of this plan.
