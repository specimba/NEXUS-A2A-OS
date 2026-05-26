# Provider-routing smoke result — 2026-05-26 18:06 UTC

## Test
Dispatch one cheap message via `openclaw agent --agent main --message "Respond with PONG"`
through the gateway (token exported in shell only, never printed).

## Result: BLOCKED — provider mapping failure

```
GatewayClientRequestError: FailoverError:
No API key found for provider "openai".
Auth store: /root/.openclaw/agents/main/agent/auth-profiles.json
Configure auth for this agent (openclaw agents add <id>)
or copy only portable static auth profiles from the main agentDir.
```

Latency until error: 6722 ms.

## Diagnosis

`openclaw models list` for agent `main` shows exactly one entry:

```
Model                  Input  Ctx   Local  Auth  Tags
openai/gpt-5.5         text   195k  no     no    default
```

But `agents/main/agent/models.json` declares 4 providers:
- `nvidia_nim`  (api_key_present: True)
- `kilocode`   (api_key_present: True)
- `openrouter` (api_key_present: True)
- `github-copilot` (api_key_present: False)

**Conclusion**: provider-routing failure as predicted. The active model selector resolves to
`openai/gpt-5.5` (the OpenClaw "Pi default"), which requires an OpenAI key we do not have
and do not intend to add. The configured NIM/KiloCode/OpenRouter providers exist on disk
but the agent's registered model list does not include any model from those providers.

## Why ModelRelay/NIM-via-Zo-Space works while this fails

They are different code paths:
- **ModelRelay route at `specimba.zo.space/api/modelrelay/chat`** calls NVIDIA NIM directly
  with `NVDIA_NIM_KEY2` from a Hono route. It bypasses OpenClaw entirely.
- **Native OpenClaw agent runtime** dispatches through the gateway, looks up the agent's
  registered model, hits the failover chain, and fails when it cannot find an OpenAI key
  because the default model still targets OpenAI.

ModelRelay success is NOT proof that the OpenClaw native provider path is wired.

## What needs to happen (proposal only — not executed)

1. Add NIM models to the agent's registered model list, e.g. via `openclaw agents add`
   pointing to one of the nvidia_nim models such as `deepseek-ai/deepseek-v4-flash`.
2. Set that model as the agent default and demote `openai/gpt-5.5` (or remove it from
   the agent's registry — it is the platform default, not the operator default).
3. Re-run this smoke test and capture: served provider, served model, latency, status.
4. Only after that does "native OpenClaw provider routing" actually pass.

## Hard boundary

I will NOT change the agent default model registration in this slice.
That belongs in the next bounded slice with explicit operator approval and a clean
backup of `models.json` / agent config first.
