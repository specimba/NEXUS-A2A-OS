---
id: NODE-MIG-TRANSITION_MANIFEST
authority_scope: experimental
origin_sha256: e1a16b7fd54b524da63202baed46769c7f4d61d070c6bd1f296c65ac517cec85
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-6BC5B0
---
# NEXUS Docs Transition Manifest

**Generated**: 2026-06-04  
**Purpose**: Master checklist for reorganizing `docs/` into a governed, category-based structure.

## New Directory Structure

```
docs/
├── governance/          (7 files) — constitutional, policy, framework
├── operations/          (14 files) — runbooks, deployment, guides, provider configs
├── research/            (25 files) — analysis, evaluations, model deep dives, paper extracts
├── security/            (14 files) — audit reports, incident reports, hardening, forensics
├── coordination/        (16 files) — agent coordination, grounding, state digests, integration
├── reviews/             (3 files) — system audits, status reports, asset inventories
├── handbook/            (4 files) — CLI guide, workflow style, boot guide, not-doing list
├── wiki/                (3 files) — README + graph validation
├── archive/             (40+ files) — stale, superseded, completed incident reports
│   ├── gross/           — completed GROSS investigation
│   ├── handoff/         — historical handoff reports
│   ├── research/        — superseded evals, stale checkpoints, raw JSON
│   └── root/            — archived root-level docs
└── hermes/              → DELETE (move NEXUS_MAIN_SOUL.md to governance/)
```

---

## SUMMARY

| Action | Count |
|--------|-------|
| MOVE   | 60    |
| ARCHIVE| 45    |
| DELETE | 40    |
| KEEP   | 35    |
| **TOTAL** | **180** |

---

## 1. MOVES

Files that change directory to their proper category.

### 1.1 From `docs/` root to proper category

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 1 | `docs/A2A_ZAPIER_MCP_INTEGRATION_ARCHITECTURE.md` | `docs/operations/A2A_ZAPIER_MCP_INTEGRATION_ARCHITECTURE.md` | MOVE | Integration architecture → operations |
| 2 | `docs/DEPLOYMENT_RUNBOOKS.md` | `docs/operations/DEPLOYMENT_RUNBOOKS.md` | MOVE | Deployment runbooks → operations |
| 3 | `docs/FUSION_REALITY_CHECK.md` | `docs/operations/FUSION_REALITY_CHECK.md` | MOVE | Fusion check → operations |
| 4 | `docs/IMPLEMENTATION_UPGRADE_RECOMMENDATIONS.md` | `docs/research/IMPLEMENTATION_UPGRADE_RECOMMENDATIONS.md` | MOVE | Upgrade analysis → research |
| 5 | `docs/IMPROVEMENT_FRAMEWORK_V2.md` | `docs/governance/IMPROVEMENT_FRAMEWORK_V2.md` | MOVE | Framework → governance |
| 6 | `docs/MIGRATION_STRATEGY_AZURE_TO_HYBRID.md` | `docs/operations/MIGRATION_STRATEGY_AZURE_TO_HYBRID.md` | MOVE | Migration strategy → operations |
| 7 | `docs/NEXUS_CONNECTIVITY_REPORT.md` | `docs/research/NEXUS_CONNECTIVITY_REPORT.md` | MOVE | Connectivity analysis → research |
| 8 | `docs/NEXUS_OS_VISION_MANIFEST_2026.md` | `docs/governance/NEXUS_OS_VISION_MANIFEST_2026.md` | MOVE | Vision manifest → governance |
| 9 | `docs/SOURCE_ANALYSIS_FINAL_SUMMARY.md` | `docs/research/SOURCE_ANALYSIS_FINAL_SUMMARY.md` | MOVE | Source analysis → research |

### 1.2 From `docs/handoff/` to proper categories

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 10 | `docs/handoff/ANTIGRAVITY_CLAIMS_VERIFICATION_2026-05-24.md` | `docs/security/ANTIGRAVITY_CLAIMS_VERIFICATION_2026-05-24.md` | MOVE | Security verification → security |
| 11 | `docs/handoff/BENCHMARK_TRUST_REGISTRY.md` | `docs/research/BENCHMARK_TRUST_REGISTRY.md` | MOVE | Benchmark registry → research |
| 12 | `docs/handoff/BOUNCER_MODEL_MATRIX_2026-05-24.md` | `docs/research/BOUNCER_MODEL_MATRIX_2026-05-24.md` | MOVE | Model matrix → research |
| 13 | `docs/handoff/CONTAMINATION_DETECTION_UNIFIED_2026-05-26.md` | `docs/research/CONTAMINATION_DETECTION_UNIFIED_2026-05-26.md` | MOVE | Detection research → research |
| 14 | `docs/handoff/DEVIN_KIMI_GUARD_PLANE_NEXT_MISSION_2026-05-24.md` | `docs/security/DEVIN_KIMI_GUARD_PLANE_NEXT_MISSION_2026-05-24.md` | MOVE | Guard plane mission → security |
| 15 | `docs/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_TRIAGE_2026-05-26.md` | `docs/security/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_TRIAGE_2026-05-26.md` | MOVE | Security triage → security |
| 16 | `docs/handoff/ERNIE_SECURITY_REMEDIATION_REPORT_2026-05-23.md` | `docs/security/ERNIE_SECURITY_REMEDIATION_REPORT_2026-05-23.md` | MOVE | Security remediation → security |
| 17 | `docs/handoff/ERNIE_SESSION02_DEEP_ANALYSIS_2026-05-23.md` | `docs/research/ERNIE_SESSION02_DEEP_ANALYSIS_2026-05-23.md` | MOVE | Session analysis → research |
| 18 | `docs/handoff/ERNIE_SESSION05_NEXUS_FRONTIER_V4_SYNTHESIS_2026-05-25.md` | `docs/research/ERNIE_SESSION05_NEXUS_FRONTIER_V4_SYNTHESIS_2026-05-25.md` | MOVE | Frontier synthesis → research |
| 19 | `docs/handoff/ERNIE_SESSION06_NEXUS_STRATEGY_SYNTHESIS_2026-05-25.md` | `docs/research/ERNIE_SESSION06_NEXUS_STRATEGY_SYNTHESIS_2026-05-25.md` | MOVE | Strategy synthesis → research |
| 20 | `docs/handoff/ERNIE_SUPREMACY_INVESTIGATION_REPORT_2026-05-22.md` | `docs/security/ERNIE_SUPREMACY_INVESTIGATION_REPORT_2026-05-22.md` | MOVE | Investigation report → security |
| 21 | `docs/handoff/GENIUSTURTLE_NEXUS_ADAPTER_CONTRACT_2026-05-26.md` | `docs/coordination/GENIUSTURTLE_NEXUS_ADAPTER_CONTRACT_2026-05-26.md` | MOVE | Adapter contract → coordination |
| 22 | `docs/handoff/GROK_LONGRUN_MCP_AUTOMATION_REVIEW_2026-05-25.md` | `docs/research/GROK_LONGRUN_MCP_AUTOMATION_REVIEW_2026-05-25.md` | MOVE | Automation review → research |
| 23 | `docs/handoff/GROK_UPLOAD_QUEUE_SECURITY_INCIDENT_2026-05-27.md` | `docs/security/GROK_UPLOAD_QUEUE_SECURITY_INCIDENT_2026-05-27.md` | MOVE | Security incident → security |
| 24 | `docs/handoff/GROSS_GROK_LEAK_LAB_FINDINGS_LONG_SESSION_2026-05-27.md` | `docs/security/GROSS_GROK_LEAK_LAB_FINDINGS_LONG_SESSION_2026-05-27.md` | MOVE | Leak lab findings → security |
| 25 | `docs/handoff/GUARD_PLANE_V7_VERIFICATION_REPORT_2026-06-02.md` | `docs/security/GUARD_PLANE_V7_VERIFICATION_REPORT_2026-06-02.md` | MOVE | Verification report → security |
| 26 | `docs/handoff/META_ATTACK_DETECTOR_V3_GAPS_2026-05-24.md` | `docs/security/META_ATTACK_DETECTOR_V3_GAPS_2026-05-24.md` | MOVE | Attack detector gaps → security |
| 27 | `docs/handoff/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | `docs/security/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | MOVE | Secret hardening → security |
| 28 | `docs/handoff/NEXUS_TWAVE_QWAVE_DOPPELGROUND_GENIUSTURTLE_INTEGRATION_SCAN_2026-05-26.md` | `docs/coordination/NEXUS_TWAVE_QWAVE_DOPPELGROUND_GENIUSTURTLE_INTEGRATION_SCAN_2026-05-26.md` | MOVE | Integration scan → coordination |
| 29 | `docs/handoff/NEXUS_VISIBLE_LAYERS_ACTIVE_INTEGRATION_BLUEPRINT_2026-05-26.md` | `docs/coordination/NEXUS_VISIBLE_LAYERS_ACTIVE_INTEGRATION_BLUEPRINT_2026-05-26.md` | MOVE | Integration blueprint → coordination |
| 30 | `docs/handoff/NEXUS_VISIBLE_LAYERS_EXECUTION_PROGRESS_2026-05-26.md` | `docs/coordination/NEXUS_VISIBLE_LAYERS_EXECUTION_PROGRESS_2026-05-26.md` | MOVE | Execution progress → coordination |
| 31 | `docs/handoff/OLLAMA_ENV_AND_AGENT_RUNTIME_FIX_2026-05-26.md` | `docs/operations/OLLAMA_ENV_AND_AGENT_RUNTIME_FIX_2026-05-26.md` | MOVE | Runtime fix → operations |
| 32 | `docs/handoff/PAPERS02_SYNTHESIS_AND_ACTIONABLE_INSIGHTS_2026-05-26.md` | `docs/research/PAPERS02_SYNTHESIS_AND_ACTIONABLE_INSIGHTS_2026-05-26.md` | MOVE | Papers synthesis → research |
| 33 | `docs/handoff/PREMIUM_PROVIDER_LIVE_VALIDATION_2026-06-02.md` | `docs/operations/PREMIUM_PROVIDER_LIVE_VALIDATION_2026-06-02.md` | MOVE | Provider validation → operations |
| 34 | `docs/handoff/QWAVE_TWAVE_ARTIFACT_LEDGER_2026-05-26.json` | `docs/coordination/QWAVE_TWAVE_ARTIFACT_LEDGER_2026-05-26.json` | MOVE | Artifact ledger → coordination |
| 35 | `docs/handoff/RP_MODEL_BOUNCER_BENCHMARK_V2_2026-05-23.md` | `docs/research/RP_MODEL_BOUNCER_BENCHMARK_V2_2026-05-23.md` | MOVE | Benchmark V2 → research |
| 36 | `docs/handoff/STRESS_LAB_DATASET_ROADMAP_2026-05-22.md` | `docs/research/STRESS_LAB_DATASET_ROADMAP_2026-05-22.md` | MOVE | Dataset roadmap → research |
| 37 | `docs/handoff/automation-hygiene/AUTOMATION_AUDIT_2026-05-23.md` | `docs/operations/AUTOMATION_AUDIT_2026-05-23.md` | MOVE | Automation audit → operations |
| 38 | `docs/handoff/cline-agent-analysis.md` | `docs/research/cline-agent-analysis.md` | MOVE | Agent analysis → research |
| 39 | `docs/handoff/codex-agent-patterns.md` | `docs/research/codex-agent-patterns.md` | MOVE | Agent patterns → research |
| 40 | `docs/handoff/grok-longrun/README.md` | `docs/operations/grok-longrun-README.md` | MOVE | Long-run README → operations |
| 41 | `docs/handoff/multi-agent-grounding-report.md` | `docs/coordination/multi-agent-grounding-report.md` | MOVE | Grounding report → coordination |
| 42 | `docs/handoff/multi-agent-sync-failure.md` | `docs/coordination/multi-agent-sync-failure.md` | MOVE | Sync failure → coordination |
| 43 | `docs/handoff/nexusclaw/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md` | `docs/research/NEXUSCLAW_CORE_V0_EVIDENCE_MATRIX_2026-06-03.md` | MOVE | Evidence matrix → research |
| 44 | `docs/handoff/pdf_extracts/` (all 13 .txt files) | `docs/research/paper_extracts/` (all 13 files) | MOVE | Paper extracts → research |
| 45 | `docs/handoff/zo-coordination/README.md` | `docs/coordination/zo-coordination-README.md` | MOVE | Coordination README → coordination |
| 46 | `docs/handoff/zo-coordination/INTERN_AI_PROVIDER_BOOT_2026-06-03.md` | `docs/operations/INTERN_AI_PROVIDER_BOOT_2026-06-03.md` | MOVE | Provider boot → operations |
| 47 | `docs/handoff/zo-coordination/NEXUS_STATE_DIGEST.json` | `docs/coordination/NEXUS_STATE_DIGEST.json` | MOVE | State digest → coordination |
| 48 | `docs/handoff/zo-coordination/OPENROUTER_AUTO_OPENCLAW_GROK_INTEGRATION_2026-05-25.md` | `docs/operations/OPENROUTER_AUTO_OPENCLAW_GROK_INTEGRATION_2026-05-25.md` | MOVE | OpenRouter integration → operations |
| 49 | `docs/handoff/zo-coordination/ZO_24_7_PROVIDER_BACKUP_PLAN_2026-05-24.md` | `docs/operations/ZO_24_7_PROVIDER_BACKUP_PLAN_2026-05-24.md` | MOVE | Backup plan → operations |
| 50 | `docs/handoff/zo-coordination/ZO_AUTOMATION_REGISTRY.md` | `docs/operations/ZO_AUTOMATION_REGISTRY.md` | MOVE | Automation registry → operations |
| 51 | `docs/handoff/zo-coordination/ZO_LONG_RUN_DIRECTIVE_2026-05-22.md` | `docs/coordination/ZO_LONG_RUN_DIRECTIVE_2026-05-22.md` | MOVE | Long run directive → coordination |
| 52 | `docs/handoff/zo-coordination/ZO_OPENCLAW_CONFUSION_HELP_PROMPT_2026-05-26.md` | `docs/coordination/ZO_OPENCLAW_CONFUSION_HELP_PROMPT_2026-05-26.md` | MOVE | Confusion prompt → coordination |
| 53 | `docs/handoff/zo-coordination/ZO_OPENCLAW_MODELRELAY_DIGEST_2026-05-24.md` | `docs/coordination/ZO_OPENCLAW_MODELRELAY_DIGEST_2026-05-24.md` | MOVE | Model relay digest → coordination |
| 54 | `docs/handoff/zo-coordination/ZO_OPENCLAW_NEXT_SAFE_SLICE_2026-05-26.md` | `docs/coordination/ZO_OPENCLAW_NEXT_SAFE_SLICE_2026-05-26.md` | MOVE | Safe slice → coordination |
| 55 | `docs/handoff/zo-coordination/ZO_OPENCLAW_REACHABILITY_AND_SWARM_WORKLOGS_2026-05-26.md` | `docs/coordination/ZO_OPENCLAW_REACHABILITY_AND_SWARM_WORKLOGS_2026-05-26.md` | MOVE | Reachability worklogs → coordination |

### 1.3 From `docs/other/` to proper categories

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 56 | `docs/hermes/NEXUS_MAIN_SOUL.md` | `docs/governance/NEXUS_MAIN_SOUL.md` | MOVE | Soul document → governance |
| 57 | `docs/research/ENTERPRISE_GOVERNANCE_MODEL.md` | `docs/governance/ENTERPRISE_GOVERNANCE_MODEL.md` | MOVE | Governance model → governance |
| 58 | `docs/research/ERNIE_FORENSIC_COMPUTATIONAL_AUDIT.md` | `docs/security/ERNIE_FORENSIC_COMPUTATIONAL_AUDIT.md` | MOVE | Forensic audit → security |
| 59 | `docs/research/ernie_remediation/UPGRADED_INTELLIGENCE_PLAN_2026-05-23.md` | `docs/security/UPGRADED_INTELLIGENCE_PLAN_2026-05-23.md` | MOVE | Intelligence plan → security |
| 60 | `docs/operations/nexus_agentic_gateway_v31_deep_dive_2026-04-18.md` | `docs/archive/nexus_agentic_gateway_v31_deep_dive_2026-04-18.md` | MOVE | Deep dive → archive (stale) |

### 1.4 From root to `docs/`

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 61 | `GROUNDING_SYNTHESIS_2026-06-02.md` | `docs/research/GROUNDING_SYNTHESIS_2026-06-02.md` | MOVE | Synthesis → research |
| 62 | `MCP_SETUP_GUIDE.md` | `docs/operations/MCP_SETUP_GUIDE.md` | MOVE | Setup guide → operations |
| 63 | `NEXUS_AGENT_PROTOCOL.md` | `docs/governance/NEXUS_AGENT_PROTOCOL.md` | MOVE | Agent protocol → governance |
| 64 | `NEXUS_DOCKER_MCP_SET1_ANALYSIS.md` | `docs/research/NEXUS_DOCKER_MCP_SET1_ANALYSIS.md` | MOVE | MCP analysis → research |
| 65 | `NEXUS_DOCKER_MCP_SET1_ROADMAP.md` | `docs/operations/NEXUS_DOCKER_MCP_SET1_ROADMAP.md` | MOVE | MCP roadmap → operations |
| 66 | `NEXUS_SET2_TESTED_INTEGRATION_TESTS.md` | `docs/research/NEXUS_SET2_TESTED_INTEGRATION_TESTS.md` | MOVE | Integration tests → research |
| 67 | `NEXUS_SET2_TESTED_MCP_SELECTION.md` | `docs/research/NEXUS_SET2_TESTED_MCP_SELECTION.md` | MOVE | MCP selection → research |
| 68 | `NEXUS_TRUST_MEMORY_CORE_PLAN_2026-06-03.md` | `docs/governance/NEXUS_TRUST_MEMORY_CORE_PLAN_2026-06-03.md` | MOVE | Trust memory plan → governance |
| 69 | `SLACK_BOT_SETUP.md` | `docs/operations/SLACK_BOT_SETUP.md` | MOVE | Slack bot setup → operations |
| 70 | `SYSTEM_AUDIT_REPORT_2026-05-29.md` | `docs/reviews/SYSTEM_AUDIT_REPORT_2026-05-29.md` | MOVE | System audit → reviews |
| 71 | `cline_agent_review.md` | `docs/handoff/cline-agent-review.md` | MOVE | Agent review → handoff (temporary) |
| 72 | `P0_PHASE_COMPLETION.txt` | `docs/handoff/P0_PHASE_COMPLETION.txt` | MOVE | Phase completion → handoff |
| 73 | `NEXUS_OS_STATUS_REPORT.md` | `docs/reviews/NEXUS_OS_STATUS_REPORT.md` | MOVE | Status report → reviews |
| 74 | `NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` | `docs/operations/NEXUS_ZO_CLAW_INTEGRATION_PLAN.md` | MOVE | Integration plan → operations |
| 75 | `DATASET_EXPANSION_COMPLETION_REPORT.md` | `docs/reviews/DATASET_EXPANSION_COMPLETION_REPORT.md` | MOVE | Completion report → reviews |
| 76 | `INSPIRATION.md` | `docs/research/INSPIRATION.md` | MOVE | Inspiration → research |
| 77 | `worklog.md` | `docs/operations/worklog-root.md` | MOVE | Root worklog → operations (if different from docs/operations/worklog.md) |

---

## 2. ARCHIVES

Files that move to `docs/archive/` (stale, superseded, completed incident reports).

### 2.1 From `docs/` root and subdirectories

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 78 | `docs/INVESTIGATION_REPORT_2026-05-20.md` | `docs/archive/INVESTIGATION_REPORT_2026-05-20.md` | ARCHIVE | Completed investigation |
| 79 | `docs/SOURCE_ANALYSIS_FINDINGS_REPORT.md` | `docs/archive/SOURCE_ANALYSIS_FINDINGS_REPORT.md` | ARCHIVE | Superseded by FINAL_SUMMARY |
| 80 | `docs/SOURCE_ANALYSIS_PLAN.md` | `docs/archive/SOURCE_ANALYSIS_PLAN.md` | ARCHIVE | Completed plan |
| 81 | `docs/gross/DISK_CLEANUP_ANALYSIS_REPORT_2026-05-31.md` | `docs/archive/gross/DISK_CLEANUP_ANALYSIS_REPORT_2026-05-31.md` | ARCHIVE | Completed GROSS report |
| 82 | `docs/gross/GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026-05-31.md` | `docs/archive/gross/GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026-05-31.md` | ARCHIVE | Completed GROSS report |
| 83 | `docs/gross/SMART_ELIMINATION_REPORT_2026-05-31.md` | `docs/archive/gross/SMART_ELIMINATION_REPORT_2026-05-31.md` | ARCHIVE | Completed GROSS report |
| 84 | `docs/gross/WSL_GROK_BUILD_EXPERIMENT_REPORT_2026-05-31.md` | `docs/archive/gross/WSL_GROK_BUILD_EXPERIMENT_REPORT_2026-05-31.md` | ARCHIVE | Completed GROSS report |
| 85 | `docs/gross/gross_xai_security_report.md` | `docs/archive/gross/gross_xai_security_report.md` | ARCHIVE | Completed GROSS report |
| 86 | `docs/handoff/2026-05-17-governance-endpoints.md` | `docs/archive/handoff/2026-05-17-governance-endpoints.md` | ARCHIVE | Historical handoff |
| 87 | `docs/handoff/2026-05-20-nexusalpha-pr32-safe-push.md` | `docs/archive/handoff/2026-05-20-nexusalpha-pr32-safe-push.md` | ARCHIVE | Historical handoff |
| 88 | `docs/handoff/2026-05-20-pi-broken.md` | `docs/archive/handoff/2026-05-20-pi-broken.md` | ARCHIVE | Historical handoff |
| 89 | `docs/handoff/ANTIGRAVITY_IDE_BUG_REPORT_2026-05-23.md` | `docs/archive/handoff/ANTIGRAVITY_IDE_BUG_REPORT_2026-05-23.md` | ARCHIVE | Completed bug report |
| 90 | `docs/handoff/BEAST_MODE_DIRECTIVE_COMPLETION_REPORT_2026-05-26.md` | `docs/archive/handoff/BEAST_MODE_DIRECTIVE_COMPLETION_REPORT_2026-05-26.md` | ARCHIVE | Completed directive |
| 91 | `docs/handoff/BEAST_MODE_SESSION_COMPLETION_2026-05-26.md` | `docs/archive/handoff/BEAST_MODE_SESSION_COMPLETION_2026-05-26.md` | ARCHIVE | Completed session |
| 92 | `docs/handoff/BLIND_SPOT_V4_PROBE_RESULTS.json` | `docs/archive/handoff/BLIND_SPOT_V4_PROBE_RESULTS.json` | ARCHIVE | Completed probe results |
| 93 | `docs/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_FREEZE_2026-05-26.json` | `docs/archive/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_FREEZE_2026-05-26.json` | ARCHIVE | Completed ledger |
| 94 | `docs/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_MAIN_2026-05-26.json` | `docs/archive/handoff/DOPPELGROUND_GITLEAKS_FALSE_POSITIVE_LEDGER_MAIN_2026-05-26.json` | ARCHIVE | Completed ledger |
| 95 | `docs/handoff/ERNIE_A2B_IMAGE_LONG_RUN_LAST_MESSAGE_2026-05-26.md` | `docs/archive/handoff/ERNIE_A2B_IMAGE_LONG_RUN_LAST_MESSAGE_2026-05-26.md` | ARCHIVE | Historical session |
| 96 | `docs/handoff/GROSS_PHASE2_EXECUTION_PLAN_2026-05-29.md` | `docs/archive/handoff/GROSS_PHASE2_EXECUTION_PLAN_2026-05-29.md` | ARCHIVE | Completed execution plan |
| 97 | `docs/handoff/GUARD_PLANE_V13_VERIFICATION_REPORT_2026-05-24.md` | `docs/archive/handoff/GUARD_PLANE_V13_VERIFICATION_REPORT_2026-05-24.md` | ARCHIVE | Superseded by V7 |
| 98 | `docs/handoff/LOCAL_RESOURCE_MONITOR_2026-05-27.md` | `docs/archive/handoff/LOCAL_RESOURCE_MONITOR_2026-05-27.md` | ARCHIVE | Historical monitor |
| 99 | `docs/handoff/MODEL_DEEP_DIVE_INTEL_DISTILLATION_2026-05-25.md` | `docs/archive/handoff/MODEL_DEEP_DIVE_INTEL_DISTILLATION_2026-05-25.md` | ARCHIVE | Duplicate of research/ copy |
| 100 | `docs/handoff/MODEL_LAB_JOB_CARD_EXAMPLE_CHECK_2026-05-26.json` | `docs/archive/handoff/MODEL_LAB_JOB_CARD_EXAMPLE_CHECK_2026-05-26.json` | ARCHIVE | Completed check |
| 101 | `docs/handoff/NEXUS_DOCKER_WSL_USAGE_OPTIMIZATION_2026-05-18.md` | `docs/archive/handoff/NEXUS_DOCKER_WSL_USAGE_OPTIMIZATION_2026-05-18.md` | ARCHIVE | Historical optimization |
| 102 | `docs/handoff/NEXUS_LOCAL_GROUNDING_REFRESH_2026-05-24.md` | `docs/archive/handoff/NEXUS_LOCAL_GROUNDING_REFRESH_2026-05-24.md` | ARCHIVE | Completed refresh |
| 103 | `docs/handoff/NEXUS_LOCAL_RESTART_RECOVERY_2026-05-18.md` | `docs/archive/handoff/NEXUS_LOCAL_RESTART_RECOVERY_2026-05-18.md` | ARCHIVE | Historical recovery |
| 104 | `docs/handoff/NEXUS_VENDOR_AGENT_HYGIENE_2026-05-18.md` | `docs/archive/handoff/NEXUS_VENDOR_AGENT_HYGIENE_2026-05-18.md` | ARCHIVE | Historical hygiene report |
| 105 | `docs/handoff/OLLAMA_CLEANUP_RECOVERY_2026-05-25.md` | `docs/archive/handoff/OLLAMA_CLEANUP_RECOVERY_2026-05-25.md` | ARCHIVE | Completed recovery |
| 106 | `docs/handoff/RP_MODEL_BOUNCER_BENCHMARK_2026-05-22.md` | `docs/archive/handoff/RP_MODEL_BOUNCER_BENCHMARK_2026-05-22.md` | ARCHIVE | Superseded by V2 |
| 107 | `docs/handoff/SESSION_AUTONOMOUS_2026-05-22.md` | `docs/archive/handoff/SESSION_AUTONOMOUS_2026-05-22.md` | ARCHIVE | Completed session |
| 108 | `docs/handoff/STREAMLABS_OBS_CRASH_AND_BACKGROUND_WORKLOAD_INVESTIGATION_2026-05-26.md` | `docs/archive/handoff/STREAMLABS_OBS_CRASH_AND_BACKGROUND_WORKLOAD_INVESTIGATION_2026-05-26.md` | ARCHIVE | Completed investigation |
| 109 | `docs/handoff/STREAMLABS_OBS_CRASH_FOLLOWUP_2026-05-25.md` | `docs/archive/handoff/STREAMLABS_OBS_CRASH_FOLLOWUP_2026-05-25.md` | ARCHIVE | Completed followup |
| 110 | `docs/handoff/STREAMLABS_OBS_HEALTH_INVESTIGATION_2026-05-23.md` | `docs/archive/handoff/STREAMLABS_OBS_HEALTH_INVESTIGATION_2026-05-23.md` | ARCHIVE | Completed investigation |
| 111 | `docs/handoff/grok-longrun/inbox/grok-0001.md` | `docs/archive/handoff/grok-longrun-inbox-grok-0001.md` | ARCHIVE | Historical inbox |
| 112 | `docs/handoff/grok-longrun/state/feature_list.json` | `docs/archive/handoff/grok-longrun-feature_list.json` | ARCHIVE | Historical state |
| 113 | `docs/handoff/grok-longrun/state/progress.jsonl` | `docs/archive/handoff/grok-longrun-progress.jsonl` | ARCHIVE | Historical progress |
| 114 | `docs/handoff/model_lab_job_card.example.json` | `docs/archive/handoff/model_lab_job_card.example.json` | ARCHIVE | Example card |
| 115 | `docs/handoff/nexus-tidiness/` (all 14 files) | `docs/archive/handoff/nexus-tidiness/` (keep subdirectory intact) | ARCHIVE | Completed tidiness project |
| 116 | `docs/research/GUARD_EVAL_REPORT_2026-05-20.md` | `docs/archive/research/GUARD_EVAL_REPORT_2026-05-20.md` | ARCHIVE | Superseded eval report |
| 117 | `docs/research/MEMORY_CHECKPOINT_CURRENT.md` | `docs/archive/research/MEMORY_CHECKPOINT_CURRENT.md` | ARCHIVE | Stale checkpoint |
| 118 | `docs/research/ernie_remediation/remediation_report.md` | `docs/archive/research/ernie_remediation-remediation_report.md` | ARCHIVE | Duplicate of security/ copy |
| 119 | `docs/research/guard_eval_full_results.json` | `docs/archive/research/guard_eval_full_results.json` | ARCHIVE | Raw eval results |
| 120 | `docs/research/guard_eval_results.json` | `docs/archive/research/guard_eval_results.json` | ARCHIVE | Raw eval results |
| 121 | `docs/research/guard_eval_scored_results.json` | `docs/archive/research/guard_eval_scored_results.json` | ARCHIVE | Raw eval results |
| 122 | `docs/reviews/NEXUS_ASSET_INVENTORY_AND_INTEGRATION_2026-05-12.md` | `docs/archive/reviews/NEXUS_ASSET_INVENTORY_AND_INTEGRATION_2026-05-12.md` | ARCHIVE | Superseded inventory |

### 2.2 From root to `docs/archive/root/`

| # | Current Path | New Path | Action | Reason |
|---|-------------|----------|--------|--------|
| 123 | `2026-05-20-alpha-branch-comparison.md` | `docs/archive/root/2026-05-20-alpha-branch-comparison.md` | ARCHIVE | Historical comparison |
| 124 | `2026-05-20-pi-broken.md` | `docs/archive/root/2026-05-20-pi-broken.md` | ARCHIVE | Duplicate |
| 125 | `NEO_NEXUS_GROUNDING.md` | `docs/archive/root/NEO_NEXUS_GROUNDING.md` | ARCHIVE | Historical grounding |
| 126 | `NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | `docs/archive/root/NEXUS_DOCKER_SECRET_HARDENING_2026-05-19.md` | ARCHIVE | Duplicate |
| 127 | `conversation_history_full_export_2026-05-27.md` | `docs/archive/root/conversation_history_full_export_2026-05-27.md` | ARCHIVE | Historical export |
| 128 | `nexus_grounding_report.md` | `docs/archive/root/nexus_grounding_report.md` | ARCHIVE | Historical grounding |
| 129 | `session-ses_1e41.md` | `docs/archive/root/session-ses_1e41.md` | ARCHIVE | Historical session |
| 130 | `CURATED_RESEARCH_AND_AGENT_LOGS_SYNTHESIS.md` | `docs/archive/root/CURATED_RESEARCH_AND_AGENT_LOGS_SYNTHESIS.md` | ARCHIVE | Historical synthesis |

---

## 3. DELETES

Temp files, test outputs, scratch, duplicates, placeholders.

| # | Current Path | Action | Reason |
|---|-------------|--------|--------|
| 131 | `.tmp_gross_canonical.ps1` | DELETE | Temp script |
| 132 | `.tmp_gross_counts.ps1` | DELETE | Temp script |
| 133 | `.tmp_gross_envs.ps1` | DELETE | Temp script |
| 134 | `.tmp_gross_grounding.ps1` | DELETE | Temp script |
| 135 | `.tmp_gross_largest.ps1` | DELETE | Temp script |
| 136 | `.tmp_gross_logs.ps1` | DELETE | Temp script |
| 137 | `.tmp_gross_mentions.out` | DELETE | Temp output |
| 138 | `.tmp_gross_mentions.ps1` | DELETE | Temp script |
| 139 | `.tmp_gross_mentions_filt.out` | DELETE | Temp output |
| 140 | `.tmp_gross_mentions_filtered.ps1` | DELETE | Temp script |
| 141 | `.tmp_gross_mentions_fixed.out` | DELETE | Temp output |
| 142 | `.tmp_gross_mentions_fixed.ps1` | DELETE | Temp script |
| 143 | `.tmp_gross_phase_plans.ps1` | DELETE | Temp script |
| 144 | `.tmp_gross_plans.out` | DELETE | Temp output |
| 145 | `.tmp_gross_plans_fixed.ps1` | DELETE | Temp script |
| 146 | `.tmp_gross_recon.ps1` | DELETE | Temp script |
| 147 | `.tmp_gross_research.ps1` | DELETE | Temp script |
| 148 | `.tmp_gross_topfiles.out` | DELETE | Temp output |
| 149 | `.tmp_gross_topfiles.ps1` | DELETE | Temp script |
| 150 | `investigate_awcc.ps1` | DELETE | Temp script |
| 151 | `scan_downloads_gross.ps1` | DELETE | Temp script |
| 152 | `triage.py` | DELETE | Temp script |
| 153 | `triage_full.py` | DELETE | Temp script |
| 154 | `_tmp_run_guard_eval2.py` | DELETE | Temp script |
| 155 | `AGENT_WELCOME_PROMPTS.md` | DELETE | Placeholder |
| 156 | `GROSS_PROJECT_STATE_4AGENT.md` | DELETE | Duplicate |
| 157 | `GROSS_SESSION27_WARMUP.md` | DELETE | Scratch |
| 158 | `zo-claw-confusion-snapshot.md` | DELETE | Scratch |
| 159 | `zo_pub_7Ln55LCVcOuqGM6y_snapshot.md` | DELETE | Scratch |
| 160 | `.pytest_final.txt` | DELETE | Test output |
| 161 | `.pytest_result.txt` | DELETE | Test output |
| 162 | `create_output.txt` | DELETE | Test output |
| 163 | `full_test_output.txt` | DELETE | Test output |
| 164 | `test_output.txt` | DELETE | Test output |
| 165 | `test_results.txt` | DELETE | Test output |
| 166 | `test_results_full.txt` | DELETE | Test output |
| 167 | `Getting Started.md` | DELETE | Placeholder |
| 168 | `docs/handoff/grok-longrun/accepted/.gitkeep` | DELETE | Placeholder |
| 169 | `docs/handoff/grok-longrun/outbox/.gitkeep` | DELETE | Placeholder |
| 170 | `docs/handoff/grok-longrun/rejected/.gitkeep` | DELETE | Placeholder |

---

## 4. KEEPS

Files that stay in place (canonical root files, already-correct docs/ files).

### 4.1 Canonical root files

| # | Current Path | Action | Reason |
|---|-------------|--------|--------|
| 171 | `AGENTS.md` | KEEP | Canonical root |
| 172 | `SOUL.md` | KEEP | Canonical root |
| 173 | `CLAUDE.md` | KEEP | Canonical root |
| 174 | `HEARTBEAT.md` | KEEP | Canonical root |
| 175 | `GROUNDING.md` | KEEP | Canonical root |
| 176 | `NEXUS_OS_V4_MASTER_PLAN.md` | KEEP | Canonical root |
| 177 | `README.md` | KEEP | Canonical root |
| 178 | `knowledge.md` | KEEP | Canonical root |
| 179 | `01_PROJECT_STATE.md` | KEEP | Canonical root |
| 180 | `CONTRIBUTING.md` | KEEP | Canonical root |
| 181 | `NEXT_MOVEMENTS_PLAN.txt` | KEEP | Canonical root |
| 182 | `PROJECT_GROUNDING_LEDGER.md` | KEEP | Canonical root (or verify if docs/coordination/ copy is canonical) |

### 4.2 Already correct in `docs/`

| # | Current Path | Action | Reason |
|---|-------------|--------|--------|
| 183 | `docs/governance/ACTIVATION_LANES.md` | KEEP | Already in correct location |
| 184 | `docs/governance/NEXUS_CONSTITUTION.md` | KEEP | Already in correct location |
| 185 | `docs/governance/NEXUS_GOVERNANCE_RECONCILE_2026-05.md` | KEEP | Already in correct location |
| 186 | `docs/handbook/03_NEXUSCTL_GUIDE.md` | KEEP | Already in correct location |
| 187 | `docs/handbook/05_NEXUS_AFK_WORKFLOW_STYLE.md` | KEEP | Already in correct location |
| 188 | `docs/handbook/08_C_KILOCLAW_FASTBOOT.md` | KEEP | Already in correct location |
| 189 | `docs/handbook/NOT_DOING_LIST.md` | KEEP | Already in correct location |
| 190 | `docs/operations/NEXUS_TIDINESS_PROTOCOL.md` | KEEP | Already in correct location |
| 191 | `docs/operations/worklog.md` | KEEP | Already in correct location |
| 192 | `docs/research/ANCHORED_SUMMARY_2026-06-03.md` | KEEP | Already in correct location |
| 193 | `docs/research/BOUNCER_RP_MODEL_ANALYSIS_2026-05-22.md` | KEEP | Already in correct location |
| 194 | `docs/research/DELETED_MODELS_THEORETICAL_INVENTORY.md` | KEEP | Already in correct location |
| 195 | `docs/research/GUARD_MODEL_COMBINATION_REPORT_2026-05-24.md` | KEEP | Already in correct location |
| 196 | `docs/research/MCP_SECURITY_PAPERS_2026-05-20.md` | KEEP | Already in correct location |
| 197 | `docs/research/MERGE_STRATEGY_DEEP_DIVE_2026-05-22.md` | KEEP | Already in correct location |
| 198 | `docs/research/MODEL_DEEP_DIVE_DISTILLATION_2026-05-25.md` | KEEP | Already in correct location |
| 199 | `docs/research/MODEL_SWEEP_REPORT_2026-05-24.md` | KEEP | Already in correct location |
| 200 | `docs/research/NEXUSCLAW_DESIGN.md` | KEEP | Already in correct location |
| 201 | `docs/research/OPTIMAL_LOCAL_MULTI_MODEL_SERVING_2026-05-26.md` | KEEP | Already in correct location |
| 202 | `docs/research/model_analysis_and_guarding_strategies.md` | KEEP | Already in correct location |
| 203 | `docs/wiki/README.md` | KEEP | Already in correct location |
| 204 | `docs/wiki/graph/nexusctl_wiki_check_2026-05-26.json` | KEEP | Already in correct location |
| 205 | `docs/wiki/graph/reviewground_wiki_check_2026-05-26.json` | KEEP | Already in correct location |

---

## 5. DEPENDENCY ORDER

Moves must be executed in this order to avoid conflicts:

1. **Create target directories first** — all new `docs/` subdirectories must exist before any files are moved into them.
2. **Archive subdirectories** — create `docs/archive/gross/`, `docs/archive/handoff/`, `docs/archive/research/`, `docs/archive/root/` before archiving.
3. **Move root-level docs** (#61–77) — move files from repo root into `docs/` before reorganizing within `docs/`.
4. **Move from `docs/` root** (#1–9) — move files from `docs/` root into proper categories.
5. **Move from `docs/handoff/`** (#10–55) — move files from handoff into proper categories.
6. **Move from `docs/hermes/` and misc** (#56–60) — move remaining misplaced files.
7. **Archive** (#78–130) — move stale/completed files to archive.
8. **Delete** (#131–170) — remove temp files, test outputs, duplicates.
9. **Verify** — run verification commands (see Section 7).

---

## 6. TARGET DIRECTORY CREATION

Create these directories before executing any moves:

```bash
mkdir -p docs/governance
mkdir -p docs/operations
mkdir -p docs/research/paper_extracts
mkdir -p docs/security
mkdir -p docs/coordination
mkdir -p docs/reviews
mkdir -p docs/handbook
mkdir -p docs/wiki/graph
mkdir -p docs/archive/gross
mkdir -p docs/archive/handoff
mkdir -p docs/archive/research
mkdir -p docs/archive/root
```

---

## 7. VERIFICATION

Run these commands after execution to confirm nothing was lost:

### 7.1 Count files before and after

```bash
# Before reorganization
echo "=== BEFORE ===" && find docs/ -type f | wc -l && echo "Root files:" && find . -maxdepth 1 -type f | wc -l

# After reorganization (should be same total)
echo "=== AFTER ===" && find docs/ -type f | wc -l && echo "Root files:" && find . -maxdepth 1 -type f | wc -l
```

### 7.2 Verify no orphaned files

```bash
# Check for files still in docs/ root (should be 0 after moves)
find docs/ -maxdepth 1 -type f

# Check for files still in docs/handoff/ (should be 0 after moves)
find docs/handoff/ -type f 2>/dev/null

# Check for files still in docs/hermes/ (should be 0 after moves)
find docs/hermes/ -type f 2>/dev/null
```

### 7.3 Verify target directories have expected content

```bash
echo "=== GOVERNANCE ===" && ls docs/governance/
echo "=== OPERATIONS ===" && ls docs/operations/
echo "=== RESEARCH ===" && ls docs/research/
echo "=== SECURITY ===" && ls docs/security/
echo "=== COORDINATION ===" && ls docs/coordination/
echo "=== REVIEWS ===" && ls docs/reviews/
echo "=== HANDBOOK ===" && ls docs/handbook/
echo "=== WIKI ===" && ls docs/wiki/
echo "=== ARCHIVE ===" && ls -R docs/archive/
```

### 7.4 Verify no files lost (compare checksums)

```bash
# Generate checksums before (save to file first)
find docs/ -type f -exec md5sum {} \; > /tmp/checksums_before.txt

# After reorganization, verify all checksums still present
while read hash file; do
  if ! grep -q "$hash" /tmp/checksums_before.txt; then
    echo "MISSING: $file"
  fi
done < <(find docs/ -type f -exec md5sum {} \;)
```

### 7.5 Git verification

```bash
git status --short
git diff --stat
```

---

## 8. NOTES

- The `docs/handoff/` directory should be **empty** after all moves and archives are complete. It can then be removed or kept as a staging area for future handoffs.
- The `docs/hermes/` directory should be **empty** after moving `NEXUS_MAIN_SOUL.md`. It can then be removed.
- The `docs/gross/` directory should be **empty** after archiving. It can then be removed.
- The `docs/research/ernie_remediation/` directory should be **empty** after archiving. It can then be removed.
- Root-level `.tmp_*`, `.pytest_*`, and test output files should be verified as not tracked by git before deletion.
- `worklog.md` at root vs `docs/operations/worklog.md` — verify they are different files before moving. If identical, keep only one.
- `PROJECT_GROUNDING_LEDGER.md` at root vs `docs/coordination/` copy — verify which is canonical before keeping.

---

*This manifest was generated as the master checklist for the NEXUS docs reorganization. Execute in dependency order and verify after each phase.*
