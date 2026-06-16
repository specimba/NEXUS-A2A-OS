# Intern AI Adapter Boot

Date: 2026-06-03
Provider id: `internai`

This directory contains secret-free adapter templates for OpenCode, KiloCode,
Zo/OpenClaw, Hermes, and ModelRelay. The original boot file contained token
material and must not be committed, copied into docs, or archived into NEXUS.

## Provider Contract

- Base URL: `https://chat.intern-ai.org.cn/api/v1`
- Chat path: `/chat/completions`
- Auth: `Authorization: Bearer $INTERN_API_KEY`
- Default quota: 30 requests/min/user
- Agent model: `intern-s2-preview`
- General model: `intern-latest`
- Vision model: `internvl2.5-latest`
- Do not send `stop`
- Send `thinking_mode: true` for Intern-S2, Intern-S1 Pro, Intern-S1, and Intern-S1 Mini

## Key Lanes

If only one extra key is available, set it as `INTERN_API_KEY_2`; OpenCode,
KiloCode, Claw, and Zo lanes will prefer it when dedicated lane keys are absent.

- Local ModelRelay: `INTERN_MODELRELAY_API_KEY`, `INTERN_API_KEY`, `INTERN_API_KEY_2`
- Hermes/GMR: `INTERN_HERMES_API_KEY`, `INTERN_API_KEY`, `INTERN_API_KEY_2`
- OpenCode: `INTERN_OPENCODE_API_KEY`, `INTERN_API_KEY_2`, `INTERN_API_KEY`
- KiloCode: `INTERN_KILOCODE_API_KEY`, `INTERN_API_KEY_2`, `INTERN_API_KEY`
- Zo/OpenClaw: `INTERN_CLAW_API_KEY`, `INTERN_ZO_API_KEY`, `INTERN_API_KEY_2`, `INTERN_API_KEY`

## Local Check

```powershell
python scripts/intern_ai_provider_check.py --lane opencode
python scripts/install_intern_ai_adapters.py --json
```

Use `--live` only when spending one provider request is acceptable:

```powershell
python scripts/intern_ai_provider_check.py --live --model intern-s2-preview --lane claw
```

## Local Adapter Copy

The installer writes only repo-local, secret-free adapter copies:

```powershell
python scripts/install_intern_ai_adapters.py --write-local
```

It does not write global OpenCode/KiloCode config, Zo secrets, or token values.

## Zo/OpenClaw

In Zo secrets, set `INTERN_BASE_URL` plus one of:

- `INTERN_CLAW_API_KEY`
- `INTERN_ZO_API_KEY`
- `INTERN_API_KEY_2`

During OpenClaw onboarding, choose a custom OpenAI-compatible provider:

- Base URL: `https://chat.intern-ai.org.cn/api/v1`
- Model: `intern-s2-preview`
- Key env: prefer `INTERN_CLAW_API_KEY`, then `INTERN_ZO_API_KEY`, then `INTERN_API_KEY_2`

After live installation and key migration are verified, delete the original
Downloads boot file or move it to a real secret vault. Do not archive it here.

