---
id: NODE-MIG-CLASSIFICATION_MANIFEST
authority_scope: experimental
origin_sha256: bd9f1969ac69a05543165a77e516b366f86badef7ce156731f7ce4e5d151a108
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-5FD127
---
# NEXUS Tidiness Classification Manifest
## Run: 2026-05-21-001353 | HEAD: f5fe558 | Rollback: codex/specimba/rollback-pre-tidiness-20260521-001353

<!-- CANARY: cb31ca58cb98b3db96ea3dcd721975db -->
---

## 1. Downloads → NEXUS (NEXUS-related documents, research, benchmarks)

### 1.1 Research Texts → `research/incoming/`
| Source | Destination | Rationale |
|---|---|---|
| `HFways.txt` | `research/incoming/` | HuggingFace research notes |
| `ciciKUS.txt` | `research/incoming/` | Research notes (context unclear, keep for review) |
| `redisMEMORYservice.txt` | `research/incoming/` | Redis memory service research |
| `geminiresearch01.txt` | `research/incoming/` | Gemini model research |
| `SLM-smol-research01.txt` | `research/incoming/` | SLM research |
| `DERDDRE-04.txt` | `research/incoming/` | DERDDRE red-team research |
| `conciousnes1.txt` | `research/incoming/` | Consciousness/AI research |
| `MCPinspirations.txt` | `research/incoming/` | MCP design notes |
| `Nebiusrelated.txt` | `research/incoming/` | Nebius cloud research |
| `therm02.txt`, `therm03.txt` | `research/incoming/` | Thermodynamics/LLM research |
| `thermoLLMfix-001.txt` | `research/incoming/` | Thermodynamic LLM fix research |
| `HALLUCINATION-001-locale-bleed.md` | `research/incoming/` | Hallucination research |
| `escapeorpoisonBLACKbox.txt` | `research/incoming/` | Black-box security research |
| `NEXUS-IMAGINE-pipeline-RAW.txt` | `research/incoming/` | Pipeline design research |
| `cyberpunk_BIG_scenario.txt` | `research/incoming/` | Scenario design |
| `AI Agents Gone Rogue.txt` | `research/incoming/` | Rogue agent research |
| `REWARD-TRY-FAIL-LEARN-001.txt` | `research/incoming/` | Learning-loop research |
| `storyline01.txt` | `research/incoming/` | Narrative/scenario research |
| `ErNIEg33.txt` | `research/incoming/` | ErNIE model research |
| `NEXUSscienceteamreport-01.txt` | `research/incoming/` | Internal science report (1.2MB) |
| `NEXUSbigLOGdeepseekV4-01.txt` | `research/incoming/` | DeepSeek V4 research log |
| `HFinternRnDtempbench-01.txt` | `research/incoming/` | HF R&D benchmark notes |
| `nemotron 3 stress test for variant Temps.txt` | `research/incoming/` | Stress test research |
| `untitled.bib`, `untitled.ris`, `untitled.csv` | `research/incoming/` | Bibliography references |
| `memoryPLAN-01.md` | `research/incoming/` | Memory architecture plan |
| `The Architecture of Global Money Control...md` | `research/incoming/` | Strategic analysis |
| `RESEARCH_BRIEF_2026-05-08.md` | `research/incoming/` | Research brief |
| `mythos_agent_orchestration_summary.txt`, `mythos_raw.txt` | `research/incoming/` | MythOS orchestration research |
| `deepsearchlinkdump-03.txt` | `research/incoming/` | Deep search link dump |
| `Scientific researcher and scientist.txt` | `research/incoming/` | Research note |
| `NEXUS approaches from others.txt` | `research/incoming/` | External NEXUS approaches |
| `Connect the A2A Tool.txt` | `research/incoming/` | A2A tooling research |
| `oracle tech threat intelligence.txt` | `research/incoming/` | Threat intelligence |
| `baseten and tensorblock.txt` | `research/incoming/` | Baseten/TensorBlock research |
| `pi and other links.txt` | `research/incoming/` | Link collection |
| `Redis capabilities and local software.txt` | `research/incoming/` | Redis research |
| `zilliz storage capabilities.txt` | `research/incoming/` | Zilliz vector DB research |
| `inkeep capabilities.txt` | `research/incoming/` | Inkeep research |
| `mem0 styled memory suggestions.txt` | `research/incoming/` | Mem0 architecture notes |
| `testcontainers guide starter.txt` | `research/incoming/` | Testcontainers guide |
| `HF_Science_database.txt` | `research/incoming/` | HF science DB |
| `gastownlog-01.txt` | `research/incoming/` | Gastown research log |
| `COMBINED_ALL_FILES.txt` | `research/incoming/` | Combined file dump |

### 1.2 Research Papers (PDFs) → `research/Papers/` (already .gitignored)
| Source | Destination | Rationale |
|---|---|---|
| `Downloads/Papers/*.pdf` (~99 files) | `research/Papers/` | Scientific papers on LLM safety, jailbreaking, multi-agent, SLMs, governance |

### 1.3 Research Images → `research/images/`
| Source | Destination | Rationale |
|---|---|---|
| `agentHARNESS.png` | `research/images/` | Agent harness diagram |
| `SLMworkflowinference.png` | `research/images/` | SLM workflow |
| `DigitalTwinAI-human.png` | `research/images/` | Digital twin diagram |
| `Visual ID workflow.png` | `research/images/` | Visual ID workflow |
| `LLMdevHallicReasons.png` | `research/images/` | Hallucination reasons diagram |
| `evoDivAgenticWorkflow.png` | `research/images/` | Evolutionary diversity workflow |
| `SLMworkflow.png` | `research/images/` | SLM workflow |
| `oldSLMexampletable.png` | `research/images/` | SLM example table |
| `PFMbasicschema.png` | `research/images/` | PFM schema |
| `ASMRtempLLM.png` | `research/images/` | ASMR/LLM temp |
| `notion_mcp_agent_preview.png` | `research/images/` | Notion MCP preview |
| `mckinsey-attack-map.jpg` | `research/images/` | Attack map |
| `UNLEARNING.png` | `research/images/` | Unlearning diagram |
| `HHvF-2sWQAMzsyD.jpg` | `research/images/` | Unknown image |
| `HICu5iaWAAArJFa.jpg` | `research/images/` | Unknown image |
| `grok-*.png`, `grok-*.jpg` | `research/images/` | Grok-generated research images |
| `V4B6N.jpg`, `UJ60Y.jpg`, `QUzgh.jpg`, `E2Y0D.jpg` | `research/images/` | Unknown images |
| `1500x500.jpg`, `image (5).jpg`–`image.jpg` | `research/images/` | Generic images |
| `gTTnhWW.png`, `image.webp`, `xneq8pasytid1.webp` | `research/images/` | Misc images |

### 1.4 Agent Logs / Handoffs → `docs/archive/downloads-logs/`
| Source | Destination | Rationale |
|---|---|---|
| `grokSKILL-MCPlog.txt` | `docs/archive/downloads-logs/` | Grok MCP session log |
| `clineMCPlog.txt` | `docs/archive/downloads-logs/` | Cline MCP session log |
| `codexCUTTEDoptimizationwork-02.txt` | `docs/archive/downloads-logs/` | Codex optimization worklog |
| `codexCUTTEDoptimizationwork-01.txt` | `docs/archive/downloads-logs/` | Codex optimization worklog |
| `NEXUSbigLOGdeepseekV4-01.txt` | `docs/archive/downloads-logs/` | DeepSeek V4 session log |
| `foundryOPUSMANerrorsonMCP-01.txt` | `docs/archive/downloads-logs/` | Foundry/MCP error log |
| `CloudflareWORKERtest.txt` | `docs/archive/downloads-logs/` | Cloudflare test log |
| `confluent_cloud_installationHELPneed-01.txt` | `docs/archive/downloads-logs/` | Confluent help log |
| `devincont-01.txt` | `docs/archive/downloads-logs/` | Devin contact/session |
| `ML-internbuildlogs-01.txt` | `docs/archive/downloads-logs/` | ML intern build logs |
| `Administrator Windows PowerShell.txt` | `docs/archive/downloads-logs/` | PowerShell session log |
| `gastownlog-01.txt` | `docs/archive/downloads-logs/` | Gastown log |

### 1.5 Plans / Requirements → `docs/archive/downloads-plans/`
| Source | Destination | Rationale |
|---|---|---|
| `GREATPLAN-01.md` | `docs/archive/downloads-plans/` | Strategic plan |
| `NotionMCPstyledPlan.txt` | `docs/archive/downloads-plans/` | Notion MCP plan |
| `notionAIinstructionSUPERprompt.md` | `docs/archive/downloads-plans/` | Notion AI prompt |
| `notionlog01.txt` | `docs/archive/downloads-plans/` | Notion session log |
| `greatA2Aconnectionlogs-01.txt` | `docs/archive/downloads-plans/` | A2A connection logs |
| `PineConePackboot.txt`, `PineConePackboot2.txt` | `docs/archive/downloads-plans/` | Pinecone boot plans |
| `TEMPtestsstart-01.txt` | `docs/archive/downloads-plans/` | Test start plan |
| `Grafanasettings.txt` | `docs/archive/downloads-plans/` | Grafana settings |
| `project-requirements-document.md` | `docs/archive/downloads-plans/` | Project requirements |
| `backend-structure-document.md` | `docs/archive/downloads-plans/` | Backend structure |
| `task-list.json` | `docs/archive/downloads-plans/` | Task list |
| `DASHBOARD.json` | `docs/archive/downloads-plans/` | Dashboard config |
| `RESEARCH_BRIEF_2026-05-08.md` | `docs/archive/downloads-plans/` | Research brief |
| `memoryPLAN-01.md` | `docs/archive/downloads-plans/` | Memory plan |

### 1.6 Scripts / Code → `scripts/archive/downloads-code/`
| Source | Destination | Rationale |
|---|---|---|
| `tts_supertonic_subagent.py` | `scripts/archive/downloads-code/` | TTS subagent script |
| `nexus_mcp.py` | `scripts/archive/downloads-code/` | MCP script |
| `check-textlogs.py` | `scripts/archive/downloads-code/` | Text log checker |
| `diagnostic_sweep.py` | `scripts/archive/downloads-code/` | Diagnostic sweep |
| `test_archivist_integrity-grok.py` | `scripts/archive/downloads-code/` | Archivist integrity test |
| `test_archivist_integrity-meta.py` | `scripts/archive/downloads-code/` | Archivist integrity test |
| `Speculative+Decoding+Technical+Report_code.js` | `scripts/archive/downloads-code/` | Speculative decoding JS |

### 1.7 Benchmarks / Datasets / Archives → `benchmarks/archive/downloads/`
| Source | Destination | Rationale |
|---|---|---|
| `dashboard-app-development.zip` | `benchmarks/archive/downloads/` | Dashboard dev archive |
| `nexus-os-week-2026-05-08-to-12.zip`, `nexus-os-week-2026-05-08-to-12` | `benchmarks/archive/downloads/` | Weekly snapshot |
| `Workflows.zip`, `Workflows` | `benchmarks/archive/downloads/` | Workflows archive |
| `hitcheck (1).zip`, `hitcheck.zip` | `benchmarks/archive/downloads/` | Hitcheck archive |
| `workspace-a7c67231...tar` | `benchmarks/archive/downloads/` | Workspace tar |
| `modelrelay.zip`, `modelrelay` | `benchmarks/archive/downloads/` | Model relay archive |
| `revisionofsources.zip` | `benchmarks/archive/downloads/` | Source revision |
| `files-d2f5095b.zip` | `benchmarks/archive/downloads/` | Unknown zip (archive) |
| `deepseek_data-2026-05-06.zip` | `benchmarks/archive/downloads/` | DeepSeek data |
| `NEXUS_OS_v3.2_Clean_Stabilization_Pack_2026-04-25.zip` | `benchmarks/archive/downloads/` | v3.2 stabilization pack |
| `NEXUS_OS_v3.2_Full_Deliverables_2026-04-25.zip` | `benchmarks/archive/downloads/` | v3.2 deliverables |
| `NEXUS_OS_v3.2_opusmanSEEKv4_Claw_System_2026-04-29.zip` | `benchmarks/archive/downloads/` | v3.2 Claw system |
| `nexusdashboards-main.zip`, `nexusdashboards-main` | `benchmarks/archive/downloads/` | Dashboards main |
| `mythOS.zip`, `mythOS` | `benchmarks/archive/downloads/` | MythOS pack |
| `pc_Windows_x86_64.zip`, `pc_Windows_x86_64` | `benchmarks/archive/downloads/` | PC build |
| `ccloud-python-client.zip`, `ccloud-python-client` | `benchmarks/archive/downloads/` | Confluent client |
| `DERDDRE.zip`, `DERDDRE` | `benchmarks/archive/downloads/` | DERDDRE dataset |

### 1.8 Speculative Decoding Reports → `docs/archive/downloads-plans/`
| Source | Destination | Rationale |
|---|---|---|
| `Speculative_Decoding_Text_Report (1).docx` | `docs/archive/downloads-plans/` | Speculative decoding report |
| `Speculative_Decoding_Text_Report.docx` | `docs/archive/downloads-plans/` | Speculative decoding report |
| `Speculative+Decoding+Technical+Report.html` | `docs/archive/downloads-plans/` | Speculative decoding report |
| `Scientific_Report.docx` | `docs/archive/downloads-plans/` | Scientific report |
| `speculativecompres.txt` | `docs/archive/downloads-plans/` | Speculative compression notes |

### 1.9 ErNIE / Model Research → `research/incoming/`
| Source | Destination | Rationale |
|---|---|---|
| `ErNIEg33_full_content.docx` | `research/incoming/` | ErNIE model research |

### 1.10 Other Research Notes → `research/incoming/`
| Source | Destination | Rationale |
|---|---|---|
| `MODEL GURU.txt` | `research/incoming/` | Model guru notes |
| `MODEL GURU codes.txt` | `research/incoming/` | Model guru code notes |
| `CRIPPLE AUTOCLAW.txt` | `research/incoming/` | Autoclaw research |
| `GatewayRequestError invalid config.txt` | `research/incoming/` | Config error research |
| `Kimi 2.6 FIX - 01.txt` | `research/incoming/` | Kimi fix notes |

---

## 2. C:\tmp → NEXUS

### 2.1 Config Backups → `docs/archive/backups/`
| Source | Destination | Rationale |
|---|---|---|
| `.modelrelay.before_literal_modelid_fix_20260505_115956.json` | `docs/archive/backups/` | ModelRelay pre-fix backup |
| `pi-settings-before-nexus-provider-fix.json` | `docs/archive/backups/` | Pi settings pre-fix backup |
| `nexus-modelrelay-mirror-before-safe-filter.ts` | `docs/archive/backups/` | ModelRelay mirror backup |
| `nexus-env-backups` | `docs/archive/backups/` | Environment backups directory |

### 2.2 Diagnostics / Logs → `docs/archive/diagnostics/`
| Source | Destination | Rationale |
|---|---|---|
| `CDB_050426-23750-01_RELOAD.txt` | `docs/archive/diagnostics/` | CDB reload diagnostic |
| `CDB_042326-34390-01.txt` | `docs/archive/diagnostics/` | CDB diagnostic |
| `CDB_050426-23750-01.txt` | `docs/archive/diagnostics/` | CDB diagnostic |
| `nexus-model-id-proxy.out.log` | `docs/archive/diagnostics/` | Model ID proxy output |
| `nexus-model-id-proxy.err.log` | `docs/archive/diagnostics/` | Model ID proxy error |
| `agt_verify_output.txt` | `docs/archive/diagnostics/` | Agent verification output |

### 2.3 Patches / PR Artifacts → `docs/archive/pr-artifacts/`
| Source | Destination | Rationale |
|---|---|---|
| `nexusalpha-pr32-comment.md` | `docs/archive/pr-artifacts/` | PR #32 comment artifact |
| `sandbox_changes.patch` | `docs/archive/pr-artifacts/` | Sandbox changes patch |
| `drs_environment.yaml` | `docs/archive/pr-artifacts/` | DRS environment definition |

### 2.4 Test Data → `datasets/archive/tmp/`
| Source | Destination | Rationale |
|---|---|---|
| `test_brotli.parquet` | `datasets/archive/tmp/` | Compression test data |
| `test_zstd.parquet` | `datasets/archive/tmp/` | Compression test data |
| `test_gzip.parquet` | `datasets/archive/tmp/` | Compression test data |
| `test_snappy.parquet` | `datasets/archive/tmp/` | Compression test data |

### 2.5 Unsure / Potentially Research → `MIXED/`
| Source | Destination | Rationale |
|---|---|---|
| `earth_science` | `MIXED/` | Unknown earth science content |

### 2.6 LEAVE IN C:\tmp (temporary / PR clones / discardable)
| Item | Action | Rationale |
|---|---|---|
| `nexusalpha-safe-push` | Leave | PR working directory |
| `nexus-governed-mcp-python-clone` | Leave | Git clone temp |
| `nexus-governed-mcp-python-pr` | Leave | Git PR temp |
| `nexus-governed-mcp-pr` | Leave | Git PR temp |
| `openclaw` | Leave | Temporary OpenClaw workspace |
| `nexus-windows-recovery-transfer` | Leave | Recovery transfer temp |
| `nexus-resource-guard` | Leave | Resource guard temp |
| `nexus_pi_active_fix_20260505_115645` | Leave | Pi fix temp directory |
| `symbols2`, `symbols` | Leave | Symbol server temp |
| `winsdksetup.exe` | Delete | Windows SDK installer |
| `qdrant` | Leave | Qdrant temp data |

---

## 3. NEXUS Root Cleanup

### 3.1 Delete Duplicates (untracked root copies already exist in proper locations)
| Root File | Proper Location | Action |
|---|---|---|
| `2026-05-18-010-docker-wsl-resource-optimization.task.md` | `tasks/done/2026-05-18-010-docker-wsl-resource-optimization.task.md` | DELETE |
| `2026-05-18-011-docker-secret-hardening.task.md` | `tasks/failed/2026-05-18-011-docker-secret-hardening.task.md` | DELETE |
| `2026-05-20-pi-broken.md` | `docs/handoff/2026-05-20-pi-broken.md` | DELETE |
| `NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | `docs/handoff/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | DELETE |

### 3.2 Move Loose Handoff Docs → `docs/handoff/`
| Root File | Destination | Rationale |
|---|---|---|
| `2026-05-20-alpha-branch-comparison.md` | `docs/handoff/` | Alpha branch comparison |
| `cline_agent_review.md` | `docs/handoff/` | Cline agent review |
| `NEO_NEXUS_GROUNDING.md` | `docs/` | NEO grounding doc |
| `nexus_grounding_report.md` | `docs/` | Grounding report |

### 3.3 Move Session Logs → `docs/archive/sessions/`
| Root File | Destination | Rationale |
|---|---|---|
| `pi-session-2026-05-12T01-45-21-849Z_019e19dc-32b8-7399-b033-ab11c960cafa.html` | `docs/archive/sessions/` | Pi session log |
| `pi-session-2026-05-15T04-08-28-478Z_019e29d2-4c3d-774b-a6a8-5d8922126d59.html` | `docs/archive/sessions/` | Pi session log |
| `session-ses_1e41.md` | `docs/archive/sessions/` | Session log |

### 3.4 Delete Temp Artifacts
| Root File | Action | Rationale |
|---|---|---|
| `_tmp_run_guard_eval2.py` | DELETE | Temp script |
| `package.json.tmp` | DELETE | Empty temp file |
| `nul` | DELETE | Null device artifact |
| `.env_backup.txt` | DELETE | Empty backup file |
| `test_heartbeat.db` | DELETE | Test artifact DB |
| `.env_corrupted_backup.txt` | DELETE | Corrupted env backup |

### 3.5 Move Backups → `docs/archive/backups/`
| Root File | Destination | Rationale |
|---|---|---|
| `.env_corrupted_backup.txt` | `docs/archive/backups/` | Corrupted env backup |

### 3.6 Leave at Root (canonical / intentional)
| Root File | Rationale |
|---|---|
| `01_PROJECT_STATE.md` | Canonical project state (AGENTS.md rule) |
| `knowledge.md` | Canonical knowledge base (AGENTS.md rule) |
| `AGENTS.md` | Agent protocol |
| `README.md` | Repository README |
| `CLAUDE.md` | Claude context |
| `SOUL.md` | Project soul |
| `HEARTBEAT.md` | Heartbeat protocol |
| `NEXUS_OS_STATUS_REPORT.md` | Status report |
| `worklog.md` | Worklog (could move to docs/operations/ but user may prefer root) |
| `pyproject.toml`, `package.json` | Package manifests |
| `nexusctl/` | CLI package |
| `nexus_os/` | Root compatibility package |
| `src/` | Source package |
| `tests/` | Test suite |
| `benchmarks/` | Benchmarks |
| `docs/` | Docs directory |
| `tasks/` | Task queue |
| `scripts/` | Scripts |
| `.gitignore`, `eslint.config.mjs`, `tsconfig.json`, etc. | Config files |
| `.env`, `.env.local` | Active env files (DO NOT TOUCH) |
| `nexus-scan.py` | Scan script (tracked? leave for now) |
| `Caddyfile`, `start.sh`, `run-dev.sh`, etc. | Infrastructure |
| `Modelfile` | Ollama modelfile |
| `nexus.db`, `nexus_api.db` | Active databases (DO NOT TOUCH) |

---

## 4. QUARANTINE / DO NOT MOVE (Secrets, Installers, Personal)

| Item | Location | Action | Rationale |
|---|---|---|---|
| `env.txt` | Downloads | DELETE or QUARANTINE | May contain secrets |
| `zilliz-cloud-nexus-os-town-username-password.txt` | Downloads | DELETE or QUARANTINE | Plaintext credentials |
| `sshkey.pem` | Downloads | DELETE or QUARANTINE | SSH private key |
| `1Password Emergency Kit A3-REHVFC-doppleground.pdf` | Downloads | DELETE or QUARANTINE | Password emergency kit |
| `password-hint.png` | Downloads | `research/images/` | AI steganography test image (password encoded in pixels); research artifact |
| `Codex Installer.exe` | Downloads | DELETE | Installer |

---

## 5. MIXED Bucket (Needs User Review)

These items are ambiguous or could fit multiple categories. Placed in `MIXED/` for manual review.

| Item | Source | Why Mixed |
|---|---|---|
| `1505` | Downloads | Unknown directory |
| `PsyTR` | Downloads | Unknown directory |
| `ClaW01.txt` | Downloads | Context unclear |
| `AIKIDOsecuritytest-01.txt` | Downloads | Could be benchmark, test, or research |
| `governor` | Downloads | Directory — unknown contents |
| `team` | Downloads | Directory — unknown contents |
| `vault` | Downloads | Directory — unknown contents |
| `ernie_mcp` | Downloads | Directory — unknown contents |
| `DOCKERaiGORDON` | Downloads | Directory — unknown contents |
| `Telegram Desktop` | Downloads | App directory — not NEXUS-related |
| `1500` | Downloads | Unknown directory |
| `DOWNLOADSDUMP` | Downloads | Dump directory — review contents |
| `doppelground_full_pack_v2` | Downloads | DoppelGround pack — may be large |
| `twave_v3_scaffold_unpacked` | Downloads | TWAVE scaffold — may duplicate src |
| `grokIMAGINEtestv1` | Downloads | Grok test — media or research? |
| `very old legacy down` | Downloads | Legacy dump |
| `NEXUS_MCP_Server_Phase6.zip` | Downloads | Already integrated — archive or delete |
| `NEXUS_MCP_Server_Phase6` | Downloads | Already integrated — archive or delete |
| `grok-video-*.mp4` | Downloads | Grok videos — media or research? |
| `tmp1x8hwzxx.mp4` | Downloads | Temp video |
| `earth_science` | C:\tmp | Unknown research directory |

---

## Pre-Execution Checklist
- [ ] Rollback branch exists: `codex/specimba/rollback-pre-tidiness-20260521-001353`
- [ ] Rollback tag exists: `rollback/pre-tidiness-20260521-001353`
- [ ] Full test suite passes: 670 passed
- [ ] No uncommitted tracked changes beyond the 4 doc/script files
- [ ] User reviewed this manifest and approves moves
