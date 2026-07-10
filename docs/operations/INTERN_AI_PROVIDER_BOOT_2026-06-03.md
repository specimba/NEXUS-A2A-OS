---
id: NODE-MIG-INTERN_AI_PROVIDER_BOOT_2026_06_03
authority_scope: experimental
origin_sha256: 0616b175cf9e22e28c019548e5a9521f99feee6bc86ce8144dbf8ce8b46bde11
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-A6AD3B
---
# Intern AI Provider Boot - Local, Zo Cloud, OpenCode, KiloCode, Hermes, Claw

Date: 2026-06-03
Source evidence: `C:/Users/speci.000/Downloads/MLinternShanghaiBOOT.txt`
Provider id: `internai`

## Capability Summary

Intern AI Shanghai ChatAPI is now modeled as an OpenAI-style chat provider for NEXUS OS.

- Base URL: `https://chat.intern-ai.org.cn/api/v1`
- Chat path: `/chat/completions`
- Auth: `Authorization: Bearer $INTERN_API_KEY`
- Default quota from boot file: `30 requests/min/user`
- Primary agent model: `intern-s2-preview`
- General model: `intern-latest`
- Vision model: `internvl3.5-latest`
- Supported: chat, streaming, tool calls, image content, long-context reasoning
- Unsupported by boot file: `stop`; NEXUS strips it for this provider
- Reasoning default: `thinking_mode=true` for `intern-s2-preview`, `intern-s1-pro`, `intern-s1`, `intern-s1-mini`

## Local Boot

Add secrets only to local runtime or `.env`; do not commit real values.

```powershell
$env:INTERN_API_KEY = "<token>"
$env:INTERN_API_KEY_2 = "<optional-second-token-for-external-agents>"
$env:INTERN_BASE_URL = "https://chat.intern-ai.org.cn/api/v1"
python scripts/intern_ai_provider_check.py
python scripts/intern_ai_provider_check.py --live --model intern-latest --lane modelrelay
```

Expected dry-run result:

- `bridge_provider_configured=true`
- `upload_provider_configured=true`
- models include `internai/intern-s2-preview`, `internai/intern-latest`, `internai/internvl3.5-latest`
- `max_context_window=256000`
- `lanes` show whether ModelRelay, Hermes, OpenCode, KiloCode, Claw, and Zo have a configured key

## Zo Computer Cloud Boot

Set the same secret names in the Zo cloud runtime, not in source control.

```text
INTERN_API_KEY=<token>
INTERN_API_KEY_2=<optional-second-token-for-external-agents>
INTERN_CLAW_API_KEY=<optional-dedicated-openclaw-token>
INTERN_ZO_API_KEY=<optional-dedicated-zo-cloud-token>
INTERN_BASE_URL=https://chat.intern-ai.org.cn/api/v1
```

Then run the same checker from the deployed workspace:

```bash
python scripts/intern_ai_provider_check.py --live --model intern-s2-preview --lane claw
```

## OpenCode / KiloCode Adapter Shape

Concrete adapter templates are now checked in under:

- `nexus_os/bridge/provider_adapters/internai/opencode-provider.json`
- `nexus_os/bridge/provider_adapters/internai/kilocode-provider.json`
- `nexus_os/bridge/provider_adapters/internai/openclaw-provider.json`
- `nexus_os/bridge/provider_adapters/internai/hermes-modelrelay-routing.json`
- `nexus_os/bridge/provider_adapters/internai/agent-lanes.json`

Use `internai` as the provider name and the OpenAI-compatible adapter surface:

```json
{
  "provider": "internai",
  "baseURL": "https://chat.intern-ai.org.cn/api/v1",
  "apiKeyEnv": "INTERN_API_KEY",
  "models": {
    "agent": "intern-s2-preview",
    "general": "intern-latest",
    "vision": "internvl3.5-latest"
  }
}
```

Recommended key lanes:

- Local ModelRelay: `INTERN_MODELRELAY_API_KEY`, then `INTERN_API_KEY`, then `INTERN_API_KEY_2`
- Hermes/GMR: `INTERN_HERMES_API_KEY`, then `INTERN_API_KEY`, then `INTERN_API_KEY_2`
- OpenCode: `INTERN_OPENCODE_API_KEY`, then `INTERN_API_KEY_2`, then `INTERN_API_KEY`
- KiloCode: `INTERN_KILOCODE_API_KEY`, then `INTERN_API_KEY_2`, then `INTERN_API_KEY`
- Zo/OpenClaw: `INTERN_CLAW_API_KEY`, then `INTERN_ZO_API_KEY`, then `INTERN_API_KEY_2`, then `INTERN_API_KEY`

If the operator only adds one more Intern key, put it in `INTERN_API_KEY_2` and use it for OpenCode, KiloCode, and Claw lanes. If more keys are available later, use the lane-specific vars above.

Adapter rules:

- Do not send `stop`.
- Send `thinking_mode: true` for `intern-s2-preview` agent/tool workloads.
- Keep tool schemas under OpenAI `tools` format.
- Treat 429 as provider cooldown, not a hard failure.

## Hermes / Claw / ModelRelay Routing

Recommended routing lanes:

- Hermes planning, research, security, and agent tasks: `internai/intern-s2-preview`
- General relay fallback: `internai/intern-latest`
- Browser or image-grounded tasks: `internai/internvl3.5-latest`

Fallback order now includes Intern AI in:

- Python upload relay: `upload/config.py`
- TypeScript ModelRelay config: `src/lib/modelrelay/config.ts`
- TypeScript AI bridge routes: `src/lib/ai-provider-bridge.ts`
- Rate-limited proxy: `src/app/api/proxy/route.ts`

Executable routing/key support now exists in:

- Python lane resolver: `upload/intern_ai_lanes.py`
- Python gateway lane selection: `upload/gateway.py`
- TypeScript key resolver: `src/lib/api-key-manager.ts`
- TypeScript AI bridge lane option: `providerLane`

Use `metadata.provider_lane` in Python ModelRelay plans and `providerLane` in TypeScript bridge requests when a caller needs a specific lane.

Example Python ModelRelay metadata:

```json
{
  "provider_lane": "opencode",
  "agent_surface": "opencode"
}
```

Example TypeScript bridge option:

```ts
await routeRequest('reasoning', messages, {
  preferModel: 'intern-s2-preview',
  providerLane: 'claw',
})
```

## Adapter Install Helper

Dry-run the local adapter copy plan:

```powershell
python scripts/install_intern_ai_adapters.py --json
```

Write repo-local reviewed adapter copies:

```powershell
python scripts/install_intern_ai_adapters.py --write-local
```

This writes only secret-free JSON under repo-local config folders such as `.opencode/providers/internai.json` and `.kilo/providers/internai.json`. It does not write global user config, Zo secrets, or token values.

## Operator Notes

- The boot file included token material; keep it out of docs and commits.
- Use `scripts/intern_ai_provider_check.py` for readiness. It is read-only by default.
- Use `--live` only when spending one provider request is acceptable.
- If OpenCode or KiloCode schema differs, keep the env contract and adapter rules above, then map the fields into their native provider config.
- After live installation and key migration are verified, delete the original boot file from Downloads or move it to a secure secret vault. Do not archive it into NEXUS.

