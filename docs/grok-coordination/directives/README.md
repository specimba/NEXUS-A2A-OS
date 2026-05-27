# Directives Outbox

Files written here by Zo automations, exported by operator (speci), and pasted into Grok 4.3 beta.

## Active Directives

Files are named `grok_directive_{timestamp}.md`. Oldest unprocessed = highest priority.

## Processing Flow

1. Zo automation writes directive → appears here
2. Operator exports the `.md` file
3. Operator opens Grok 4.3 beta, pastes the directive content
4. Grok executes the experiment and writes results to `artifacts/experiment_{id}.md`
5. Operator exports Grok's result, places in `grok-coordination/ingest/`
6. Directive file moved to `grok-coordination/queue/done/` by operator

## Urgent Directives

- `DIRECTIVE_URGENT.md` — Operator action required before next automation cycle
