# Sakana AI Fugu Configuration Guide

This document describes how to configure and run the **Sakana Fugu** and **Fugu Ultra** models inside NEXUS OS and the Codex CLI.

## 1. Environment Configuration

To use Sakana AI's models, obtain an API key from the Sakana AI Console and set it in your environment:

```powershell
$env:SAKANA_API_KEY = "your_api_key_here"
```

In production, register it inside the encrypted NEXUS vault under `NEXUS_SAKANA_API_KEY`.

## 2. Codex Configuration

Save the model catalog definition to `~/.codex/fugu.json`:

```json
{
  "models": [
    {
      "slug": "fugu",
      "display_name": "Fugu",
      "context_window": 1000000,
      "supported_reasoning_levels": [
        {
          "effort": "high",
          "description": "Deep reasoning for complex problems"
        }
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 0,
      "base_instructions": "Before recommending or running any command that could stop, restart, or replace the environment you are running in...",
      "supports_reasoning_summaries": false,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "default_verbosity": null,
      "apply_patch_tool_type": "freeform",
      "input_modalities": ["text", "image"],
      "truncation_policy": {
        "mode": "tokens",
        "limit": 10000
      },
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": []
    },
    {
      "slug": "fugu-ultra",
      "display_name": "Fugu Ultra",
      "context_window": 1000000,
      "supported_reasoning_levels": [
        {
          "effort": "high",
          "description": "Deep reasoning for complex problems"
        }
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 1,
      "base_instructions": "Before recommending or running any command that could stop, restart, or replace the environment you are running in...",
      "supports_reasoning_summaries": true,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "default_verbosity": null,
      "apply_patch_tool_type": "freeform",
      "input_modalities": ["text", "image"],
      "truncation_policy": {
        "mode": "tokens",
        "limit": 10000
      },
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": []
    }
  ]
}
```

Configure the provider block in `~/.codex/config.toml` (or `{workspace}/.codex/config.toml`):

```toml
[model_providers.sakana]
name = "Sakana API"
base_url = "https://api.sakana.ai/v1"
env_key = "SAKANA_API_KEY"
wire_api = "responses"

# Stream-Resilience Hardening Settings (Idempotent and Stateless)
stream_idle_timeout_ms = 7200000   # 2h: keep slow turns alive past Codex's 5-min default
stream_max_retries = 5             # reconnect a dropped stream instead of failing the turn
request_max_retries = 4            # retry a transient HTTP failure instead of failing the turn
```

Run Codex with Fugu:

```powershell
codex -p fugu
```

## 3. Custom Workflows & SDK Integration

```python
import os
from openai import OpenAI

# Ensure base_url ends in /v1
base_url = os.environ.get("FUGU_BASE_URL", "https://api.sakana.ai/v1").rstrip("/")
if not base_url.endswith("/v1"):
    base_url = f"{base_url}/v1"

client = OpenAI(
    api_key=os.environ["SAKANA_API_KEY"],
    base_url=base_url,
)

# Use Fugu Responses API for deep reasoning effort
response = client.responses.create(
    model="fugu-ultra",
    input="Solve the given scientific logic puzzle...",
    reasoning={
        "effort": "xhigh" # Options: high, xhigh, max
    },
    timeout=120.0
)

print(response.output_text)
```
