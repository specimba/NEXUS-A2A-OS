# LongCat Provider Adapter

LongCat is registered as a governed OpenAI-compatible cloud provider for
teacher/eval/probe work. It is not a resident core model and must not be used
as an autonomous tool executor without KAIJU/VAP approval.

## Secrets

Use environment variables only:

- `NEXUS_LONGCAT_API_KEY` canonical NEXUS key.
- `LONGCAT_API_KEY` compatibility alias.
- Lane-specific keys: `LONGCAT_MODELRELAY_API_KEY`,
  `LONGCAT_HERMES_API_KEY`, `LONGCAT_OPENCODE_API_KEY`,
  `LONGCAT_KILOCODE_API_KEY`, `LONGCAT_CLAW_API_KEY`,
  `LONGCAT_ZO_API_KEY`.

Do not copy keys from ARCHIVIST or Downloads curation files into this repo.

## Model

- `LongCat-2.0-Preview`
- Base URL: `https://api.longcat.chat/openai/v1`
- Chat path: `/chat/completions`

