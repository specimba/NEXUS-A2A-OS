# Sakana / Fugu Provider Adapter

Sakana Fugu is registered as a governed worker-selection and verifier provider.
It is not a resident core model and must not receive autonomous tool execution authority.

## Secrets

Use environment variables only:

- `NEXUS_SAKANA_API_KEY` canonical NEXUS key.
- `SAKANA_API_KEY` compatibility alias.
- `FUGU_API_KEY` compatibility alias.
- Lane keys: `SAKANA_MODELRELAY_API_KEY`, `SAKANA_HERMES_API_KEY`, `SAKANA_VERIFIER_API_KEY`.

## Models

- `fugu`
- `fugu-ultra`
- Base URL: `https://api.sakana.ai/v1`
- Chat path: `/chat/completions`
