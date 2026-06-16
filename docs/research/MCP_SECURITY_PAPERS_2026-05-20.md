---
id: NODE-MIG-MCP_SECURITY_PAPERS_2026_05_20
authority_scope: experimental
origin_sha256: ee78aeb80af3199f3c3c838d831eeb3f35392d9e943b31c373cbb53ef41592d7
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-6E8E9A
---
# MCP Security Papers — Deep Analysis

**Date**: 2026-05-20  
**Status**: Analyzed, extracted, cross-referenced  
**Papers**: 4 new arXiv papers + prior 55+ papers + 25 stress datasets

<!-- CANARY: 7aa4808200e3f3d74a7f66f00ea8a141 -->
---

## Paper 1: Enterprise-Grade Security for MCP
**arXiv:2504.08623** — Narajala (AWS) & Habler (Intuit), May 2025

### Key Contribution
First comprehensive multi-layered enterprise security framework for MCP using defense-in-depth + Zero Trust. 7 enterprise-critical threats, 9 defense domains, 3 deployment patterns.

### Attack Categories (MAESTRO 7-layer)
- MCP Server: compromise, function exploitation, DoS, communication vulns, client interference, data leakage, audit gaps, spoofing
- MCP Client: impersonation, insecure communication, operational errors, unpredictable behavior
- Host Environment: model vulns, system compromise
- Data Sources: access control, integrity, exfiltration
- Tools: misuse, resource exhaustion, tool poisoning
- Prompts: indirect manipulation (prompt injection)

### Key Defenses Proposed
1. Network segmentation (VLANs, VPC, Istio mTLS)
2. Application gateway (WAF, DPI, rate limiting, OpenTelemetry)
3. Secure containerization (immutable FS, seccomp, AppArmor)
4. Host monitoring (EDR/HIDS, FIM, memory analysis)
5. Enhanced OAuth 2.0+ (mTLS, DPoP, JIT, MFA)
6. Tool security (SAST/DAST/SCA, behavioral baselining, crypto signing)
7. Zero Trust client (per-request auth, UEBA)
8. Output filtering/DLP (ICAP, redaction)
9. Operational security (SIEM, SOAR, threat intel)

### Limitations
Conceptual/architectural only — no empirical validation, no attack success rates. Performance overhead acknowledged.

---

## Paper 2: When MCP Servers Attack
**arXiv:2509.24272** — Zhao et al. (NUS & PKU), Sep 2025

### Key Contribution
First systematic study treating MCP servers as active threat actors. 12-category component-based attack taxonomy with empirical cross-host cross-LLM evaluation. Server generator produces 1M+ unique malicious servers.

### 12 Attack Categories (A1-A12)
| ID | Category | Avg ASR | Key Subtypes |
|---|---|---|---|
| A1 | Server Metadata Poisoning | 94% | Deceptive/promotional metadata, malicious auth metadata |
| A2 | Server Configuration Abuse | 100% | Over-privileged launch params, adversarial connection params, persistence, rug pull |
| A3 | Initialization Logic Attack | 100% | Malicious code execution, endpoint exposure, DoS |
| A4 | Tool Metadata Poisoning | 89.3% | Selection inducement, info overcollection, control-flow hijack, tool impersonation |
| A5 | Tool Logic Attack | 100% | Malicious code, elicitation abuse, sampling abuse, DoS |
| A6 | Tool Output Attack | 100% | Control-flow hijack, info propagation, disinformation, phishing, DoS |
| A7 | Resource Metadata Poisoning | 66.7% | Selection inducement, type confusion, impersonation, overcollection |
| A8 | Resource Logic Attack | 100% | Malicious code, DoS, completion manipulation, sampling abuse |
| A9 | Resource Output Attack | 67.8% | Inconsistent/distorted output, instruction injection, binary payload, DoS |
| A10 | Prompt Metadata Poisoning | N/A | Selection inducement, impersonation, overcollection |
| A11 | Prompt Logic Attack | 100% | Malicious code, completion manipulation |
| A12 | Prompt Output Attack | 46.7% | User intent distortion (in-task/extra-task injection) |

### Key Empirical Results
- **6 categories at 100% ASR** across all host-LLM combinations (A2, A3, A5, A6, A8, A11)
- **3 hosts**: Claude Desktop, Cursor, fast-agent
- **5 LLMs**: GPT-4o, o3, Claude Sonnet 4, Claude Opus 4, Gemini 2.5 Pro
- **mcp-scan detects only 3.3%** (4/120)
- **AI-Infra-Guard**: ~$0.50/scan, ~10 min/scan, unreliable on subtle text attacks
- **System prompts matter more than model capability**: switching fast-agent prompt to Cursor's dropped A4 ASR from 100% to 6.7%
- **GPT-4o showed better resistance** to tool metadata poisoning than Claude/Gemini in some configurations

---

## Paper 3: MCP Landscape, Security Threats, and Future Research
**arXiv:2503.23278** — Hou et al. (HUST), Oct 2025

### Key Contribution
First comprehensive MCP ecosystem analysis with 4-phase server lifecycle and 16 threat scenarios. Catalogued 26 server collections.

### Lifecycle (4 Phases, 16 Activities)
1. **Creation**: metadata definition, capability declaration, code implementation, slash command definition
2. **Deployment**: server release, installer deployment, environment setup, tool registration
3. **Operation**: intent analysis, external resource access, tool invocation, session management
4. **Maintenance**: version control, configuration change, access audit, log audit

### 4 Attacker Types, 16 Threat Scenarios
- **Malicious Developer**: namespace typosquatting, tool name conflict, PMA, tool poisoning, rug pulls, cross-server shadowing, command injection/backdoor
- **External Attacker**: installer spoofing, indirect prompt injection
- **Malicious User**: credential theft, sandbox escape, tool chaining abuse, unauthorized access (SSE hijacking)
- **Security Flaws**: re-deployment of vulnerable versions, post-update privilege persistence, configuration drift

### Ecosystem Stats
- 26 major MCP collections catalogued
- MCPWorld: 26,404 servers; MCP.so: 16,592; Glama: 9,415; Smithery: 6,888
- 300 sampled from MCP.so: 30 non-MCP, 18 inactive
- 5 unofficial auto-installers identified

---

## Paper 4: First Look at MCP Security Issues
**arXiv:2510.16558** — Li & Gao (U Delaware), Apr 2026 — **Accepted to DSN 2026**

### Key Contribution
First cross-entity security study (hosts, registries, servers) analyzing 67,057 servers. MCPInspect pre-integration analysis tool.

### Two-Stage Attack Surface

**Stage I: Registry-Level (Pre-Integration)**
| Attack | Finding |
|---|---|
| Incomplete Server Info | 6.75% invalid links on mcp.so, 4.25% empty content on MCP Store |
| Credential Leakage | 5 valid GitHub tokens on mcp.so configuration examples |
| Maintainer Hijacking | 212 of 1,379 (15.37%) invalid-linked accounts re-registrable |
| Redirection Hijacking | 304 GitHub redirected accounts reclaimable |
| Affix-Squatting | 408 same-name groups on npm; 80.6% from different maintainers |

**Stage II: Post-Integration**
- **Tool Poisoning**: crafted descriptions/error messages induce unintended operations (ASR up to 100%)
- **Tool Shadowing**: malicious description distorts benign tool's parameters
- **Tool Confusion**: Cursor always invokes first-listed tool on name collision
- **Context-Dangling Tool**: All 4 hosts invoke tools that no longer exist but remain in LLM context history

### Tool Poisoning ASR (Table II)
| Host | LLM | Built-in Tools | Request Info | Server-Provided |
|---|---|---|---|---|
| Cursor | GPT-4o | 80-100% | 0-100% | 0-60% |
| Cursor | Claude Sonnet 4 | 100% | 100% | 60-80% |
| Cursor | Gemini 2.5 Pro | 80-100% | 100% | 80-100% |
| Windsurf | GPT-4o | 20-80% | 20-40% | 40% |
| Windsurf | Claude Sonnet 4 | 100% | 100% | 60-100% |
| Windsurf | Gemini 2.5 Pro | 100% | 100% | 80-100% |
| Cline | GPT-4o | 40-100% | 100% | 0-60% |
| Cline | Claude Sonnet 4 | 100% | 100% | 80-100% |
| Cline | Gemini 2.5 Pro | 100% | 100% | 100% |

### MCPInspect Results
- 833 vulnerable servers across decentralized registries (1.24%)
- 18 suspicious tool descriptions
- 90.24% precision (4 false positives of 41)
- Limited to Python + JavaScript/TypeScript

### Key Gemini Finding
Gemini 2.5 Pro identifies abnormal instructions but follows them anyway — safety awareness without safety enforcement.

---

## Cross-Cutting Analysis

### Coverage Matrix
| Attack Vector | Paper 1 | Paper 2 | Paper 3 | Paper 4 |
|---|---|---|---|---|
| Tool Poisoning | Core (L3) | A4/A5/A6 (100%) | Core threat | 18 servers, high ASR |
| Data Exfiltration | Key threat | A6 (100%) | Via tool chain | Via poisoning |
| Server Impersonation | Spoofing | A1/A4 impersonation | Typosquatting | Affix-squatting, redirect hijack |
| DoS | Listed | A2/A3/A5/A6/A8/A9 | Not primary | Not primary |
| Supply Chain/Rug Pull | Update compromise | A2 rug pull (100%) | Rug pulls, vulnerable versions | Credential leakage, maintainer hijack |
| Prompt Injection | Indirect manipulation | A12 output attack | Indirect prompt injection | Tool poisoning via descriptions |

### Best Source Per Dimension
| Dimension | Best Source |
|---|---|
| Enterprise Mitigation | Paper 1 (Narajala) |
| Empirical Attack Success Rates | Paper 2 (Zhao) |
| Lifecycle Threat Analysis | Paper 3 (Hou) |
| Large-Scale Registry Measurement | Paper 4 (Li & Gao) |
| Attack Taxonomy Breadth | Paper 2 (12 categories) + Paper 3 (16 scenarios) |
| Host Vulnerability Analysis | Paper 2 (3 hosts) + Paper 4 (4 hosts) |
| Automated Defense Tooling | Paper 4 (MCPInspect) |
| Multi-Stakeholder Responsibility | Paper 2 (Fig. 8 roles) |

### Key Contradictions / Surprises
1. **GPT-4o resistance is host-dependent**: 0% ASR on Cursor (Paper 2 A4) but 100% on fast-agent — system prompts matter more than model capability
2. **Gemini 2.5 Pro identifies but complies** with abnormal instructions (Paper 4) — safety awareness ≠ safety enforcement
3. **All 4 hosts lack independent verification** of LLM-selected tools (Paper 4) — fundamental architectural flaw
4. **Existing scanners nearly useless**: mcp-scan 3.3% detection rate (Paper 2)
5. **Registry ecosystem is actively compromised**: 212 hijackable accounts, 304 redirect hijacks, 5 valid tokens leaked (Paper 4)

### Gaps Not Covered By Any Paper
- Behavioral baseline anomaly detection over long time horizons
- Cross-agent collusion detection across different MCP server providers
- Memory poisoning detection in agent conversation history
- Tool output integrity verification (output schema enforcement)
- Delegation chain tracking across multi-hop MCP calls
- Quantitative defense rate measurement against v5/v6 stress datasets

---

## Mapping to RED-BLUE-PURPLE Stress Datasets

These 4 papers validate the attack vectors in our 200K+ stress records:

| Dataset | Records | Covered By Papers |
|---|---|---|
| v5 MCP Contamination | 3,000 | Papers 1-4 (all cover tool poisoning, shadowing) |
| v5 Gov Bypass | 3,000 | Papers 1, 3 (lifecycle, enterprise controls) |
| v5 Memory Poison | 3,000 | **Not covered by any paper** (gap) |
| v5 Jailbreak | 2,000 | Papers 2 (A12 prompt output), 3 (indirect injection) |
| v6 TAMAS Multi-Agent | 684 | **Not covered** (papers focus on single MCP server) |
| v6 Tool-Scored Thermo | 5,760 | Partially — Papers 2, 4 validate tool-level attacks |

---

## Implications for NEXUS 7-Layer Governance Model

| Layer | Validated By | Empirically Confirmed | Still Speculative |
|---|---|---|---|
| L1 Statistical Scorer | Papers 1, 2 (statistical baselines) | Keyword detection fails (15%) | Embedding-based scoring not tested |
| L2 Identity Chain | Paper 1 (OAuth, JIT) | Registry hijacking confirmed (Paper 4) | Delegation chain tracking |
| L3 Tool Integrity | Papers 1, 2, 4 | Tool poisoning real (up to 100% ASR) | Manifest hashing, runtime verification |
| L4 Consensus | Paper 3 (lifecycle auditing) | Hosts lack verification (Paper 4) | Byzantine multi-agent consensus |
| L5 Sequence Analysis | Paper 2 (A6 control-flow hijack) | Sequential attacks work (A6 100%) | N-gram pattern detection |
| L6 Data Flow Provenance | Paper 2 (A9 output poisoning) | Output manipulation works (67.8-100%) | Cross-tool provenance tracking |
| L7 Behavioral Baseline | Paper 1 (behavioral rules) | Not empirically measured | Long-horizon anomaly detection |

**Key takeaway**: Our 7-layer model covers vectors that even the best academic paper (Paper 2/4) doesn't address (memory poison, multi-agent collusion, long-horizon behavioral baselines). But we need empirical validation against the stress datasets to measure true stacked defense rate.
