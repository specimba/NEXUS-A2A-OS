# NEXUS OS v3.2 — Port Map

| Port | Service | Purpose |
|------|---------|---------|
| 7352 | Governance API | Primary NEXUS API — auth, proposals, trust scores, VAP proofs |
| 7353 | TWAVE wrapper | Execution engine (read-only from outside) |
| 7354 | Mock / fallback | Dev/testing only |

Verify before use: `curl http://localhost:PORT/health`
