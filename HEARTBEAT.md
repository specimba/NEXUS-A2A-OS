# HEARTBEAT.md — Moveable Strategy

## T+00: Boot & Sync

1. Configure git identity:
   ```
   git config --global user.name 'Cloud-Orchestrator'
   git config --global user.email 'cloud@nexus.os'
   ```
2. Sync state:
   ```
   git pull origin main
   ```

## T+10: Sanitize & Scan (Phase 0 Priority)

1. Read the codebase. Identify stale references, unused imports, and orphaned files.
2. Write Python scripts using `requests` (with browser User-Agent headers, NEVER raw curl) for external recon:
   ```python
   headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
   ```
3. If a site blocks you 3 times, mark it `[CIRCUIT_OPEN]` and stop trying.
4. Write `nexus-scan.py` as a DRY-RUN ONLY provenance scanner. It must map hashes and output JSON, but never auto-commit.

## T+20: Task Delegation

1. Read `handoff/from_local/`. If the Local Agent has posted Model Arena results, synthesize them into `docs/model_evaluations.md`.
2. Create new tasks for the Local Agent in `handoff/to_local/`:
   - Each task is a `.task.md` file with: title, description, acceptance criteria, deadline
   - Example: "Run 3 matches in mini_arena.py between gemma4:e2b and nemotron-3-nano:4b"
3. Review TrustEngine v2.2 metrics and flag any agents in CDR CASCADE or COLLAPSE stage.

## T+30: GVAW Handoff

1. Run `git status`. Check for:
   - New scripts or sanitization rules
   - Handoff tasks created
   - State file updates
2. If changes exist:
   ```
   git add <explicit-paths-only>
   git commit -m "orchestrator: [action description]"
   git push
   ```
3. If no changes, log `[STANDBY]`. Do not force a push.

## Circuit Breaker Protocol

| Source | Fail Count | Status | Action |
|--------|-----------|--------|--------|
| HuggingFace API | 0 | [CIRCUIT_CLOSED] | Normal queries |
| ArXiv API | 0 | [CIRCUIT_CLOSED] | Normal queries |
| NVD JSON API | 0 | [CIRCUIT_CLOSED] | Normal queries |
| Any source | 3+ | [CIRCUIT_OPEN] | Skip for rest of heartbeat |

## State Tracking

- Current CDR stages for all agents → logged in `handoff/cdr_status.json`
- Trust velocity anomalies → flagged in `handoff/trust_alerts.json`
- Vault health → checked via `SecretStore.check_health()`

## Response

If no tasks require deep reasoning, and the cycle is complete, reply exactly with:
```
HEARTBEAT_OK
```
