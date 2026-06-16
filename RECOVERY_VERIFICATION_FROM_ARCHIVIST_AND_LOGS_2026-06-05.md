NEXUS MAIN FOLDER RECOVERY VERIFICATION
Date: 2026-06-05 (post model switch note)
Source dirs inspected: C:\Users\speci.000\Downloads\ARCHIVIST and C:\Users\speci.000\Downloads\NEXUSlogs
NEXUS main location checked: C:\Users\speci.000\Documents\NEXUS (and WSL /mnt/c equivalent)

PURPOSE
Verify which artifacts from previous sessions (especially last 2026-06-02 NemoClaw / ZO Claw session) are present after reported "nexus main folder delete accident from on agent".
Use the two provided download dirs as evidence sources for missing or unverified locations.
Confirm work can continue with retrieved items.
Note and retrieve/create from logs what cannot be verified in live filesystem.

VERIFIED PRESENT (matching last session descriptions from logs)
1. NEXUS_ZO_CLAW_INTEGRATION_PLAN.md
   - Location: docs/operations/NEXUS_ZO_CLAW_INTEGRATION_PLAN.md
   - Evidence: search_files found it; read_file confirmed header id NODE-MIG-NEXUS_ZO_CLAW_INTEGRATION_PLAN, 382 lines, ~17k bytes.
   - Matches log references (e.g. NEXUSbackendOPENCODEm3log-01.txt: 21449 bytes written, 318 lines, 2026-06-02; current version close, content about Zo/OsmanClaw A2A, Kafka bridge, integration options).
   - Status: Retrieved and intact.

2. research/intake/2026-06-nvidia-spark-nemoclaw-nexus-decision.md
   - Location: research/intake/2026-06-nvidia-spark-nemoclaw-nexus-decision.md
   - Evidence: search_files found it; read_file: 124 lines, exactly 15040 bytes. Header matches: Date 2026-06-02, context follow-up to ZO plan, inspection of NVIDIA Spark links, OpenClaw vs NemoClaw decision, references to NEXUS_OS_V4_MASTER_PLAN.md, master plan gaps (sandbox, TerminalSanitizer, KAIJU, etc.).
   - Exact match to compacted memory and NEXUSlogs descriptions.
   - Status: Fully retrieved.

3. 2026-06-02-nemoclaw-wsl2-adoption.task.md
   - Location: tasks/pending/2026-06-02-nemoclaw-wsl2-adoption.task.md
   - Evidence: ls tasks/pending/ showed it (9544 bytes, Jun 3).
   - Also done/ has related governance task.
   - Status: Retrieved, matches "Lane A task" in logs.

4. Supporting last-session / recent artifacts
   - docs/research/GROUNDING_SYNTHESIS_2026-06-02.md : present (search_files hits).
   - docs/TRANSITION_MANIFEST.md : present (2026-06-04, details docs reorg into governance/operations/research/security/coordination/reviews/handbook/wiki/archive/hermes; 60 moves, 45 archives, etc.).
   - 01_PROJECT_STATE.md : present (core thesis, boundaries, architecture map matching 8-pillar style).
   - AGENTS.md, GROUNDING.md, NEXUS_OS_STATUS_REPORT.md, README.md, SOUL.md : present at root.
   - tasks/ structure: pending/, done/, failed/, templates/ with prior tasks.
   - research/intake/ : has the nemoclaw decision + 2026-06-03-nexusclaw-architectural-decision.md .
   - docs/ reorganized per manifest (operations/ has the ZO plan, research/ has grounding and intake).
   - .git present; multiple agent dirs (.claude, .codex, .devin, .grok, .kilo, .openacp, .opencode, .pi etc.); .nexus_pi, .nexus_diagnostics, backups/.
   - v4 plans and related doc with codes/ : exists but nearly empty (only src/ subdir). Likely consolidated into docs/ during reorg or affected by delete.

MISSING / UNVERIFIED (from last visit references in logs and ARCHIVIST)
1. NEXUS_OS_V4_MASTER_PLAN.md (root level)
   - Expected: C:\Users\speci.000\Documents\NEXUS\NEXUS_OS_V4_MASTER_PLAN.md (1,182 lines, 56KB, 12-week architecture roadmap, 15 sections TOC).
   - Current: File not found (read_file error "File not found"; search_files with name globs and content patterns returned 0 for exact name; only references in other files).
   - Likely the "delete accident" target or lost during docs transition / agent action.
   - Retrieved partial from logs/ARCHIVIST:
     - From ARCHIVIST/ZoCompCLOUDsolutionslog-01.json (tool return for knowledge.md read, ~2026-05-15):
       # NEXUS OS — Canonical Knowledge Base
       **Compiled:** 2026-05-15 | **Live check:** main tracking `github/clean/security-phase-0` | **HEAD:** a14229c
       ## PROJECT IDENTITY
       Nexus OS is a governed, local-first agent operating system. Python/FastAPI governance is canonical. Next.js dashboard (port 3000) is the UI proxy. Windows = control/authoring plane; Linux/WSL = execution sandbox.
       ## 8-PILLAR ARCHITECTURE
       | Pillar | Path | Purpose |
       | Bridge | `nexus_os/bridge/` | JSON-RPC server, SDK, secrets, MCP auth, vault bridge |
       | Governor | `nexus_os/governor/` | KAIJU gates, TrustEngine v2.2, VAP proof chain, compliance |
       | Vault | `nexus_os/vault/` | 5-track memory (EVENT/TRUST/CAP/FAIL/GOV), encryption |
       | Engine | `nexus_os/engine/` | Hermes router, executor, skillsmith, tool discipline |
       | GMR | `nexus_os/gmr/` | Model rotation, circuit breaker, telemetry, domain mapping |
       | Swarm | `nexus_os/swarm/` | Foreman, worker pool, auction, OpenClaw spawner |
       | Monitoring | `nexus_os/monitoring/` | TokenGuard, counters, strategies |
       | Observability | `nexus_os/observability/` | Tracing, log compression (Squeez) |
       (Later references the v4 Master Plan as 1,182 lines, 15-section, covering sandbox abstraction, cross-agent security (4-layer), governance mesh, etc.)
     - From NEXUSlogs and ARCHIVIST/NEXUS-CLAW-01.txt, greatA2Aconnectionlogs-01.txt, TEMPtestsstart-01.txt: multiple references to it as Tier 1 canonical doc, "NEXUS_OS_V4_MASTER_PLAN.md top 100 lines (15 sections TOC)", 56KB, cross-referenced with GROSS, ZO plan, security sections (TerminalSanitizer, AgentPTY, VerifiableOutput, KAIJU cross-eval).
     - From initial memory / compacted: thesis on Windows control + Linux sandboxes, unify NEXUS + HERMES + Docker Gordon, core gaps (no sandbox, duplicate code, prompt injection, hallucination detection, E2E, hardcoded paths); security section on terminal poisoning (CWE-150), defenses (TerminalSanitizer, AgentPTY, VerifiableOutput, KAIJU).
   - Action: Partial retrieved above. Full reconstruction would require deeper extraction from large dumps (COMBINED_ALL_FILES.txt 6.7MB, codexCUTTEDoptimizationwork-*.txt, devinKIMIworklog*.txt, or other ARCHIVIST txt). Recommend re-creating from these excerpts + current 01_PROJECT_STATE.md + TRANSITION_MANIFEST + ZO/decision docs if full version needed for continuity. No full 1182-line copy located in provided archives.

2. NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md (8 steps)
   - Expected: D:\GROSS\phase3\plans\NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md (executable playbook, 8 steps, referenced with the decision artifact and task).
   - Current in C: NEXUS or pointed Downloads: Only references in NEXUSlogs/NEXUSbackendOPENCODEm3log-01.txt and ARCHIVIST/NEXUS-CLAW-01.txt (e.g. "Executable install plan: D:\GROSS\phase3\plans\...", "superceded by NEXUSCLAW, kept for reference", "Steps 0-2", "5. Show the executable plan").
   - No full file or 8-step content in C:\Users\speci.000\Downloads\ARCHIVIST or NEXUSlogs.
   - Status: Not retrieved here. Check D:\GROSS directly if the drive/mount is available. Superseded note in logs suggests NEXUSCLAW / current decision may replace it.

3. Other potential from logs / "v4 plans" dir
   - "v4 plans and related doc with codes/" : dir present but content minimal (only src/); plans likely moved to docs/ during 2026-06-04 transition (see TRANSITION_MANIFEST.md for full move/archive/delete list of 180+ items).
   - knowledge.md : referenced heavily in logs/ARCHIVIST as canonical (contains or contained master plan content); not found in current root or docs/ (searches return mentions only, no file).
   - Full GROSS / exfil recovery plans, specific handoff reports: many in ARCHIVIST (e.g. GROSS_Trillion_Dollar_Forensic_Synthesis_Report.txt, NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md) and NEXUSlogs (GROSSantigravitygeminiopuslogs-05.txt etc.); some archived in NEXUS/docs/archive/gross/ .
   - D:\ paths in general: not present in C: archives; use the logs for reconstruction.
   - No direct "delete accident" strings found in quick searches, but reorganization + agent activity (multiple .agent dirs) + empty v4 plans dir consistent with accidental or bulk delete during transition.

ARCHIVIST AND NEXUSLOGS AS RECOVERY SOURCES
- ARCHIVIST: 100+ files including plans (GREATPLAN-01.md, GOVERNANCE_VULNERABILITY_SURFACE.md, NEXUS_GROSS_MASTER_MOVEMENT_PLAN_V7.md, ERNIE_SESSION07_CLOUD_SWARM_TASK_SPEC.md, DeepWiki NEXUS MCP..., ClawCodeClaudeNEXUS-README-draft.md), large dumps (COMBINED_ALL_FILES.txt, codexCUTTEDoptimizationwork-*.txt), session logs (greatA2Aconnectionlogs-01.txt, NEXUS-CLAW-01.txt, TEMPtestsstart-01.txt, ZoCompCLOUDsolutionslog-01.json with embedded plan text).
- NEXUSlogs: 30+ detailed session transcripts (NEXUSlocalworkspaceHERMESwindowslogs-01.txt (the one previously analyzed), NEXUSv4planningCODEXlog-01/02.txt, NEXUSbackendOPENCODEm3log-01.txt (contains ZO plan write details, NemoClaw decision, install plan refs), NEXUSopencodeMAINbackendCODEdeepseekV4flashlog-*, devinKIMIworklog*, archivist_audit_jsonTEXT.txt, etc.).
- Use these to re-create: grep the txt/json for specific section titles from memory (e.g. "sandbox abstraction", "TerminalSanitizer", "KAIJU cross-eval", "12-week", "8-PILLAR"); extract and merge into new docs/ if needed.
- Example extraction already done for master plan header/identity/pillars above.

CURRENT NEXUS STATE SUMMARY (from ls, search_files, read_file)
- Root: .git, AGENTS.md, GROUNDING.md, HEARTBEAT.md, NEXUS_OS_STATUS_REPORT.md, 01_PROJECT_STATE.md (Apr 21 baseline), README.md, SOUL.md, package.json (Next.js), docs/, tasks/ (with pending nemoclaw task), research/intake/ (with decision), .nexus_diagnostics, .nexus_pi, backups/ (streamlabs obs), nexus_os/ python pkg + backups of it, multiple agent context dirs, .next/, node_modules/, etc.
- Docs reorg complete-ish (per manifest): governance/, operations/ (ZO plan), research/ (GROUNDING_SYNTHESIS, intake decisions), security/, coordination/, reviews/, handbook/, wiki/, archive/ (gross/, handoff/, research/, root/).
- Git: present (can use for history if uncommitted deletes).
- No evidence of total folder wipe; selective loss of root plans + v4 plans content + knowledge.md consistent with targeted delete or reorg side-effect.
- Hermes-related (from prior context): configs and source patches for docker_volumes (NEXUS mount) were applied in previous steps; gateway/UI stable in WSL.

RECOMMENDATIONS TO CONTINUE / FULLY RETRIEVE
- Work can continue immediately on verified items (NemoClaw adoption task, ZO integration plan, decision artifact, docs structure, tasks system).
- For lost master plan: Use the extracted text above + cross-references in current 01_PROJECT_STATE.md / TRANSITION_MANIFEST / ZO plan / decision + full dumps in ARCHIVIST (start with ZoCompCLOUDsolutionslog-01.json around line 1864 and NEXUS-CLAW-01.txt) to reconstruct. If full original needed, search D: or other backups not in the two Downloads dirs.
- Run git status / git log --oneline -10 in the NEXUS dir to check for recent deletes or untracked recovery.
- If more specific "lost" items named (e.g. particular plan or file from last visit), provide names and we can target extraction from the  logs/ARCHIVIST (e.g. "grep -A 100 'section title' biglog.txt").
- To persist this verification: this file is the artifact. Update 01_PROJECT_STATE.md or create handoff if needed.
- Clean stop for any prior processes as before.
- Next: If user confirms, we can extract more sections (e.g. full 8-pillar details, security section from other logs) or re-create a v4 master plan stub based on all evidence.

EVIDENCE SOURCES (tool outputs used)
- ls of ARCHIVIST, NEXUSlogs, NEXUS root and subdirs (tasks/pending etc.).
- search_files multiple: for ZO plan, decision, master plan refs, knowledge.md mentions, V4 files, specific plan names.
- read_file: ZO plan (head), decision (full head + size match), TRANSITION_MANIFEST (reorg details), 01_PROJECT_STATE (current thesis), NEXUS_GROSS...V7 (different plan), ZoCompCLOUD...json (embedded master plan text), NEXUS_ZO... (size).
- terminal: ls, find attempts (some timed but targeted ls succeeded), grep attempts (limited by size but ls confirmed structure).
- All cross-checked against compacted context and user-provided log references.

This confirms the majority of last session work (NemoClaw lane, ZO integration, decision) is retrieved and usable. The primary gap is the root master plan (partial text recovered). Ready for next concrete step on NEXUS work.