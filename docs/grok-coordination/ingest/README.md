# Grok Ingest Pipeline

Files placed here by the operator (speci) — exported from Grok 4.3 beta sandbox.

## Processing Rules

1. Zo's `Zo-NEXUS-Progression-Tracker` scans this directory every 12h (06:00 + 18:00 UTC+3)
2. Any `.md` file with a valid `# Result:` header is parsed
3. Findings are incorporated into `docs/progression/yyyymmdd-HHMM.md`
4. Processed files are moved to `grok-coordination/queue/done/`
5. Files without the expected format are moved to `grok-coordination/queue/failed/` with a note

## Expected Format

See `PROTOCOL.md` for the full result format specification.

Minimum required fields:
- `# Result: {directive_id}`
- `- experiment_id: exp-{timestamp}`
- `- success: {true, false, partial}`
- `## Findings` section with at least 1 numbered finding
