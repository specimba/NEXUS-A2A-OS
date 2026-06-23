# LongCat API Integration & Advantage Guide

This guide details the integration and unique advantages of using **LongCat-2.0-Preview** within the NEXUS OS agent ecosystem.

## 1. The LongCat Advantage
The **LongCat-2.0-Preview** model provides significant advantages for long-session multi-agent workflows:
- **128k Output Limit**: Supports generating extremely long responses, trace trajectories, and detailed reports without output truncation.
- **High-Performance Agentic Reasoning**: Outperforms generalist models of similar size in task-planning and multi-turn tool-calling environments.
- **OpenAI/Anthropic Protocol Compatibility**: Operates natively under standard OpenAI and Anthropic API formats, allowing seamless integration.

## 2. API Endpoint Specifications
- **OpenAI-Compatible Base URL**: `https://api.longcat.chat/openai/v1`
- **Anthropic-Compatible Base URL**: `https://api.longcat.chat/anthropic`
- **Model Name**: `LongCat-2.0-Preview`

## 3. Configuration Setup

### A. Codex Configuration
Edit `~/.codex/config.toml`:
```toml
model_provider = "codex"
model = "LongCat-2.0-Preview"
disable_response_storage = true
web_search = "disabled"

[model_providers.codex]
name = "codex"
base_url = "https://api.longcat.chat/openai/v1"
wire_api = "responses"
requires_openai_auth = true
```

Edit `~/.codex/auth.json`:
```json
{
  "OPENAI_API_KEY": "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J"  # Store securely in Vault!
}
```

### B. OpenCode Configuration
Edit `Users/***/.config/opencode/opencode.json`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "LongCat": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LongCat",
      "options": {
        "baseURL": "https://api.longcat.chat/openai",
        "apiKey": "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J"  # Store securely in Vault!
      },
      "models": {
        "LongCat-2.0-Preview": {
          "name": "LongCat-2.0-Preview"
        }
      }
    }
  }
}
```

### C. ModelRelay / GMR Config Sync
For local ModelRelay instances, the LongCat provider is added to the routing table:
```json
{
  "providers": {
    "openai-compatible:longcat": {
      "apiKey": "ak_2NX8Y89gC6BE6j21SA2gj8II2bH8J",
      "baseURL": "https://api.longcat.chat/openai/v1",
      "models": ["LongCat-2.0-Preview"]
    }
  }
}
```
*Note: Ensure the real API key is stored only in the encrypted Vault (`vault/secrets/env.txt.enc`) or set via `NEXUS_LONGCAT_API_KEY` env var.*
