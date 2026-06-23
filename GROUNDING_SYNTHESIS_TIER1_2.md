# NEXUS Grounding Synthesis — Corrected for Up-to-Date Authority
**Date:** 2026-06-22  
**Correction Trigger:** `NEXUS_LONG_RUN_INTEGRATION_CONTROL_PLAN_2026-06-20.md` + `NEO_TO_NEXUS_IMPORT_PLAN_2026-06-20.md` override earlier synthesis recommendations.  
**Rule:** NEXUS remains canonical; NEO is evidence-input only. Not a migration source.

---

## What Changed Since Earlier Synthesis

| Earlier Recommendation | Corrected Status | Authority |
|------------------------|------------------|-----------|
| NEO env sanitization + git repair (immediate) | **DEPRECATED as immediate** — read-only fsck inventory only; no repair/import without explicit operator approval | `NEXUS_LONG_RUN_INTEGRATION_CONTROL_PLAN_2026-06-20.md` §2-3; §7 approval gates |
| Import NEO modules (token efficiency) | **REJECTED** — files (DOVA/MARS/RotorQuant/Squeez/MemPalace) unverified; June 20 doc explicitly rejects "approved for execution" language | `NEO_TO_NEXUS_IMPORT_PLAN_2026-06-20.md` §3.1 |
| NEO memory architecture → NEXUS | **REJECTED** — S-P-E-W incompatible with 8-channel canonical | `NEXUS_LONG_RUN_INTEGRATION_CONTROL_PLAN_2026-06-20.md` §2 |
| Azure removal in NEO | **READ-ONLY inventory only** — actual key deletion requires separate user approval | Same + approval gates |
| AWCC removal v2 (immediate) | **DOWNGRADED** — host hygiene, not NEXUS repo issue; not referenced in any June 2026 plan; strike unless user confirms still active |

---

## Canonical Port Map (Latest Verified)

Per `NEXUS_ADVISORY_DIRECTION_SYNC.md` (June 19) + Long-Run Control Plan (June 20):
- `7350` = Node ModelRelay (primary)
- `7352` = Brain API / governance **ONLY** — Node process on 7352 = runtime drift
- `7355` = Python ModelRelay fallback
- `7356` = static dashboard (confirmed serving)
- `7357` = god_mode_proxy
- `3001` = Next.js dashboard

Stale claims like `7352 = ModelRelay` are explicitly rejected.

---

## Corrected Immediate Actions

### Operator-Approved Gates (no execution without explicit yes)
1. **Hermes restart** — Config YAML valid; restart applies new limits. Still low-risk.
2. **NEO git fsck (read-only)** — Safe inventory only. `git fsck --full --no-reflogs`
3. **Azure reference inventory in NEO (read-only)** — List refs, do not delete.
4. **Token-efficiency module existence check (read-only)** — Verify DOVA/MARS/etc don't exist.
5. **Plaintext key rotation** — `NEO_HERMES_EVIDENCE_MATRIX.md` claims keys in ARCHIVIST file `29&(][11!34.txt`. CRITICAL if still live. Requires operator verification.

### Structured Verification Pass (Safe, Read-Only)
The June 20 plan prescribes exact commands. I can run these:
```powershell
git status --short -- docs\coordination\NEO_EVIDENCE_MATRIX_2026-06-20.md docs\planning\NEO_TO_NEXUS_IMPORT_PLAN_2026-06-20.md
python -c "from nexus_os.bridge.port_registry import PortRegistry; print(PortRegistry.CANONICAL_PORTS)"
python -c "from nexus_os.api.brain_api import brain_app; print(len(brain_app.routes)); print(any('/api/stress/report' in getattr(r, 'path', '') for r in brain_app.routes))"
rg -n "7352.*ModelRelay|ModelRelay.*7352|glm-4\\.7|glm-4-7" docs nexus_os src --glob '!node_modules' --glob '!.next'
```

---

## Strategic Frame (June 20 Plan)

| Source | Role | Rules |
|--------|------|-------|
| NEXUS main | Canonical | All changes here follow NEXUS gates |
| NEO agent | Evidence input only | No import without approval; read-only fsck first |
| HERMES | Local operator agent | Stability resolved; restart required |
| GLM-5.2 | Advisory designer/reviewer | Outputs are patch proposals with SHA256; never unverified executor |
| Grok | Primary advisory lane | Shared/public access most reliable |
| Zo | Advisory command routing | No execution through Zo |

---

## What Stays Valid From Older Sources

The V4 Master Plan Phase 0-6 roadmap is still architecturally correct **for NEXUS internal work**, but NEO-specific "import" recommendations from pre-June 20 docs are now superseded. Specifically:
- Terminal Sanitizer + PTY isolation + AGENTS.md safety rule update: still valid (Phase 0, internal NEXUS)
- Sandbox Abstraction Layer: still valid (Phase 1, internal NEXUS)
- Governance mesh deduplication: still valid (NEXUS main canonical, swarm → plugin)
- Memory reconciliation: still valid (decide 5-track vs 8-channel; NEO S-P-E-W explicitly rejected)

---

## Updated Risk Register

| Risk | Status | Action |
|------|--------|--------|
| Hermes config stale in memory | HIGH if not restarted | Restart required |
| NEO misclassified as import source | RESOLVED by June 20 plan | Treat as evidence-input |
| Plaintext keys in ARCHIVIST | CRITICAL — unverified | Operator must inspect `29&(][11!34.txt` |
| Port drift (Node on 7352) | DOCUMENTED | Run port verification pass |
| AWCC host bloat | LOW/OPTIONAL — host-dependent | Await user confirmation if still active |

---

## Operator Decision Points (Revised)

1. **Restart Hermes now?** — Still valid, low-risk.
2. **Run NEO read-only fsck + Azure inventory?** — Safe; June 20 plan prescribes as first step.
3. **Run NEXUS port/route verification commands?** — Safe, read-only, June 20 plan explicitly lists them.
4. **Verify ARCHIVIST key file and rotate?** — Requires your eyes on `29&(][11!34.txt` or explicit inspection approval.
5. **AWCC removal v2?** — Downgraded; host-level, not in June 2026 plan. Story-level context: appeared because May 29 audit documented it; may already be resolved. Await your confirmation.
6. **NEXUS.zip deletion** — WSL copy deleted. Windows copy at `C:\Users\speci.000\Documents\NEXUS\NEXUS.zip` (14.9 MB) remains. Delete?
