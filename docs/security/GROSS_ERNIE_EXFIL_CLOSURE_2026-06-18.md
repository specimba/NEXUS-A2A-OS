# GROSS_ERNIE_EXFIL_CLOSURE_2026-06-18

## Closure Reason

Forensic analysis of the GROSS ERNIE exfiltration event is closed based on verified evidence from ARCHIVIST, clone1706 discovery, 24h activity report, and planning logs. The exfil was not a secret theft but a privacy violation; remediation commands were executed and the operative environment is cleared.

## Findings

- **Exfiltration**: 37.42 GB staged, NOT stolen secrets, but privacy violation
- **Queue now**: 5 files / 21,898 bytes (post opt-out)
- **Hades cluster**: hades-openbar namespace, coingecko-proxy, polygon-proxy
- **Container**: Cloud Hypervisor VM, catatonit, overlay fs
- **JWT**: TERMINAL_JWT_VAL present in container (session token)
- **K8s**: 17 services discovered, no direct NEXUS data found in remote storage
- **Trust boundary collision**: The ZO plan glosses over that the MCP bridge exposes KAIJU/VAP/Vault but KAIJU evaluates IDs, not anonymous MCP calls
- **Install blockers**: 4 hard blockers are runtime discovery, 8 soft blockers are design decisions; Tier 2/3 reports (SYSTEM_AUDIT, CURATED_RESEARCH, NEXUS_STATUS_REPORT, master plan sections 7-15) were unread and likely contain prior art for trust boundary, Hermes context, and vault exposure
- **Reference prior art**: User's prior GROK 39GB exfil scenario means GROSS already has threat-modeling language to reuse
- **Files still missing post-recovery**: NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md (not recoverable from current sources), knowledge.md (referenced in AGENTS.md but not found in repo)
- **InternAI integration verified**: 6/6 test_internai_provider_config.py tests passing; configs applied in secrets.py, domain_mapping.py, config.py, models_registry.py, quota_guard.py, gateway.py

## Actions Taken (from ARCHIVIST)

- Applied InternAI provider configuration across 6 NEXUS configuration files
- Added InternAI API key lookup to secrets.py and domain resolution to domain_mapping.py
- Updated models_registry.py with internai entries and quota_guard.py with quota limits
- Fixed gateway.py `api_key` scoping
- Verified 6/6 InternAI test suite passing
- Documented recovery verification: RECOVERY_VERIFICATION_FROM_ARCHIVIST_AND_LOGS_2026-06-05.md (12,491 bytes)

## Residual Risk

- Trust boundary between NEXUS KAIJU and NemoClaw/NEXUS-native agents not fully reconciled; MCP bridge exposes KAIJU/VAP/Vault without Hermes context continuity
- 4 runtime-discovery hard blockers remain unmapped because Tier 2/3 reports were not read before install
- NEMOCLAW_WSL2_INSTALL_PLAN_2026-06-02.md and knowledge.md still missing from current sources
- Prior GROK 39GB exfil threat-modeling language not yet reused in updated master plan sections 7-15

## Decision

Closure approved. The architecture pivot from NemoClaw install to native NEXUSCLAW build removed the immediate collision surface. The 37.42GB exfil is classified as privacy violation, not secret theft. Residual trust boundary and missing source documents are tracked as follow-up items, not blockers. No further broad refactor without a separate proposal. Validate next cycle with nexusctl cycle-check.
