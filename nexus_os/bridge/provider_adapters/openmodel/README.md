# OpenModel / DeepSeek V4 Flash Provider Adapter

OpenModel is registered as a governed OpenAI-compatible provider for the DeepSeek V4 Flash free lane.
It is demand-driven only: no background discovery, broad health polling, or copied keys from ARCHIVIST.

## Secrets

Use environment variables only:

- `NEXUS_OPENMODEL_API_KEY` canonical NEXUS key.
- `OPENMODEL_API_KEY` compatibility alias.
- Lane keys: `OPENMODEL_MODELRELAY_API_KEY`, `OPENMODEL_HERMES_API_KEY`, `OPENMODEL_OPENCODE_API_KEY`.

## Model

- `deepseek-v4-flash-free`
- Base URL: `https://api.openmodel.ai`
- Chat path: `/v1/chat/completions`
