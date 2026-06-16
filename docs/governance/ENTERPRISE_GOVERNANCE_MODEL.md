---
id: NODE-MIG-ENTERPRISE_GOVERNANCE_MODEL
authority_scope: experimental
origin_sha256: d9f9fb2da15a161e239c6ddf2c26c5d9fc1e9a347fc638e3d8a3d2b75017de5d
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-6E167E
---
# NEXUS OS Enterprise Governance Security Model

**Status**: Research Synthesis — Pre-Implementation  
**Target**: 80%+ defense rate against adversarial attacks (vs ~40-50% current enterprise)  
**Foundation**: 55+ academic papers + 200K+ stress records across v5/v6 datasets  
**Date**: 2026-05-20  
**Updated**: 2026-05-20 — Incorporated 4 new arXiv MCP security papers (2504.08623, 2509.24272, 2503.23278, 2510.16558)

<!-- CANARY: 4ec3219b7e383e2cc21d8452ed8c3d76 -->
---

## 1. Why Semantic Gates Fail

Semantic/keyword-based gates cannot be the primary defense layer:

| Attack Type | Keyword Catch Rate | Bypass Mechanism |
|---|---|---|
| Tool Chaining (4-step privilege esc) | 0% | Each call is individually benign |
| Registry Supply Chain | 0% | 1 malicious tool hidden among 10 legitimate |
| Memory Poison (conditional backdoor) | ~5% | Payload looks like legitimate KB entry |
| Font Encoding / Steg Injection | 0% | Visual chars remapped; text parser sees benign |
| Multi-Agent Collusion | 0% | Coordination happens across agents, not in prompts |
| Policy Framing Jailbreak | ~15% | "Safety audit ticket AUDIT-2026-05-14, Section 7(c)" |
| Schema Type Confusion | 0% | Schema declares valid types; runtime is different |
| Cross-Tool Output Poisoning | 0% | Data flow contamination, not direct tool call |

Even the best semantic classifiers (OpenAI Moderation, LlamaGuard) achieve ~40-60% on our v5 datasets. Keyword-only approaches get ~15%.

---

## 2. The NEXUS Approach: 7-Layer Defense Framework

Instead of evaluating individual tool calls in isolation, we analyze across **7 orthogonal security dimensions**:

```
┌─────────────────────────────────────────────────────┐
│              7-Layer Defense Stack                    │
├─────────────────────────────────────────────────────┤
│  Layer 7: Behavioral Baseline Anomaly Detection      │
│  Layer 6: Cross-Tool Data Flow Provenance            │
│  Layer 5: Sequential Pattern Analysis                │
│  Layer 4: Multi-Agent Consensus Verification         │
│  Layer 3: Runtime Tool Integrity Verification        │
│  Layer 2: Identity & Delegation Chain Tracking       │
│  Layer 1: Request-Level Statistical Scoring          │
└─────────────────────────────────────────────────────┘
```

### Layer 1: Request-Level Statistical Scoring
Not keyword matching — statistical features of the request:

- **Token distribution entropy**: Attack prompts have higher entropy in early tokens
- **Embedding similarity to known attack vectors**: Cosine distance from attack cluster centroids
- **Tool call frequency distribution**: Poisson modeling of expected call rates
- **Parameter value distribution**: Expected types, lengths, character distributions
- **Refusal pattern consistency**: If agent was recently refused, subsequent requests in same session get elevated scrutiny

Implementation: Lightweight pre-filter (Ollama embedding model) that catches ~60% of naive attacks and routes to higher layers for complex ones.

### Layer 2: Identity & Delegation Chain Tracking
Every action carries full provenance:

- **Origin agent ID**: Cryptographically signed at source
- **Delegation chain**: A→B→C→D is recorded, not lost
- **Permission scope at each hop**: Subagent gets scoped permissions, not parent's full set
- **Trust score per hop**: Each delegation decrements effective trust (decay model)
- **Re-verification triggers**: Cross-scope operations, privilege escalation, data type change

Blocks: provenance loss attacks, identity theft, consent scope creep, delegation chain exploits.

### Layer 3: Runtime Tool Integrity Verification
Tools are verified at **every invocation**, not just registration:

- **Manifest hash verification**: Compare runtime hash against signed manifest
- **Tool output integrity**: Expected output schema + statistical bounds
- **Recursive tool registry scan**: For registry collisions, check all registered names for similarity
- **Delayed activation detection**: Monitor tool behavior drift over time (not just point-in-time check)
- **Name collision detection**: Levenshtein distance / embedding similarity scan of all registered tools

Blocks: schema remapping, registry supply chain, tool name collision, metric poisoning, delayed conditional activation.

### Layer 4: Multi-Agent Consensus Verification
High-risk actions require independent verification:

- **Independent agent verification**: Agent B independently evaluates the same request without seeing Agent A's decision
- **Byzantine fault tolerance**: N-of-M consensus for critical operations
- **Free-rider detection**: If Agent B's analysis is suspiciously similar to Agent A's (cosine similarity > threshold), flag as potential collusion
- **Collusion pattern detection**: Statistical analysis of agreement rates across agent pairs
- **Verification diversity**: Require differently-trained/configured agents to cross-verify

Blocks: cascaded trust exploits, multi-agent collusion, free-rider attacks, byzantine failures.

### Layer 5: Sequential Pattern Analysis
Instead of evaluating individual calls, analyze **sequences**:

- **N-gram tool call sequences**: Compare against benign/attack sequence databases
- **Information flow tracking**: Does Tool A's output appear verbatim in Tool B's input? (poison detection)
- **Gradual escalation detection**: Slow permission creep over time (monitoring session-long patterns)
- **Tool call rate anomaly**: Sudden burst of tool calls (distraction detection)
- **Resource consumption trajectory**: Memory/CPU/API call counts growing unexpectedly
- **Inter-call timing analysis**: Unusually fast/slow patterns suggesting automated attacks vs human operation

Blocks: tool chaining privilege escalation, cross-tool output poisoning, distraction floods, overthinking loop DoS, gradual scope creep.

### Layer 6: Cross-Tool Data Flow Provenance
Track how data flows between tools:

- **Taint tracking**: Mark output of each tool call; track how it flows into other tool calls
- **Data type boundary crossing**: String→SQL→File→Network — each boundary crossing is a risk point
- **Indirect information flow**: Tool B reads data that Tool A previously wrote to shared storage
- **Output-to-input matching**: Detect when Tool A's poisoned output directly feeds Tool B's critical parameter
- **Side channel detection**: Monitor timing/error correlations between apparently unrelated tools

Blocks: cross-tool output poisoning, indirect injection through shared state, data exfiltration via chaining, SSRF chaining.

### Layer 7: Behavioral Baseline Anomaly Detection
Learn normal patterns per agent/session and detect deviation:

- **Per-agent behavioral baseline**: Normal tool call patterns, times, frequencies, parameter distributions
- **Session-to-session comparison**: Is this session's behavior significantly different from historical norms?
- **Cross-agent comparison**: Are other agents behaving normally while this one deviates?
- **Environmental context**: Time of day, recent activity, system state
- **Collective anomaly detection**: Isolated deviations are noise; correlated deviations across multiple signals raise severity

Blocks: all zero-day attacks, compromised agents, sophisticated unknown attack vectors.

---

## 3. Attack Taxonomy Coverage Map

| Attack Type | L1 Stat | L2 Identity | L3 Integrity | L4 Consensus | L5 Sequence | L6 Provenance | L7 Baseline |
|---|---|---|---|---|---|---|---|
| Schema Remapping | ○ | ● | ● | ○ | ○ | ○ | ● |
| Registry Supply Chain | ○ | ○ | ● | ● | ○ | ● | ● |
| Auth Bypass Tool | ● | ● | ● | ● | ○ | ○ | ● |
| Metric Poisoning | ○ | ○ | ● | ● | ○ | ● | ● |
| Tool Name Collision | ○ | ○ | ● | ○ | ○ | ○ | ● |
| Resource Exhaustion | ● | ● | ● | ● | ● | ○ | ● |
| Tool Chaining Escalation | ○ | ● | ○ | ● | ● | ● | ● |
| Delayed Conditional Activation | ○ | ○ | ● | ○ | ○ | ○ | ● |
| Cross-Tool Output Poison | ○ | ○ | ○ | ● | ● | ● | ● |
| Passive Influence | ○ | ○ | ○ | ● | ● | ● | ● |
| Overthinking Loop DoS | ● | ○ | ● | ○ | ● | ○ | ● |
| Scope Inheritance Violation | ○ | ● | ○ | ● | ○ | ○ | ● |
| Audit Trail Poison | ○ | ● | ○ | ○ | ○ | ○ | ● |
| Delegation Provenance Loss | ○ | ● | ○ | ● | ○ | ○ | ● |
| Policy Caching Poison | ○ | ○ | ○ | ● | ○ | ○ | ● |
| Cross-Agent Policy Inconsistency | ○ | ● | ○ | ● | ○ | ○ | ● |
| Consent Scope Creep | ○ | ● | ○ | ● | ● | ○ | ● |
| TOCTOU Policy Bypass | ○ | ○ | ● | ○ | ● | ○ | ● |
| Memory Embedding Backdoor | ○ | ○ | ○ | ● | ○ | ● | ● |
| Multi-Agent Propagation | ○ | ○ | ○ | ● | ● | ● | ● |
| Memory Graft Artifact | ○ | ○ | ○ | ● | ○ | ● | ● |
| Trust Score Poison | ○ | ○ | ● | ● | ● | ○ | ● |
| Policy Framing Jailbreak | ● | ● | ○ | ● | ○ | ○ | ● |
| Encoding/Unicode Attack | ● | ○ | ● | ○ | ○ | ○ | ● |
| Indirect Injection | ● | ● | ● | ● | ● | ● | ● |
| Payload Split | ● | ○ | ○ | ● | ● | ● | ● |
| Multi-Agent Kill Chain | ● | ● | ● | ● | ● | ● | ● |
| Stream Injection | ○ | ● | ● | ○ | ● | ○ | ● |
| TOCTOU (Tool Swap) | ○ | ● | ● | ○ | ● | ○ | ● |
| Batch Auth Bypass | ● | ● | ○ | ○ | ● | ○ | ● |
| Font Encoding | ● | ○ | ○ | ○ | ○ | ○ | ● |
| Multi-Agent Collusion | ○ | ● | ● | ● | ● | ○ | ● |

**Key**: ● = Strong defense, ○ = Indirect/no defense, Blank = Not applicable

Every attack type is covered by **at least 2 layers**. Most by 4+ layers.

---

## 4. TrustKernel Integration Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Agent / Model                           │
│  (Grok / ChatGPT / Claude / Gemini / Local)                │
└────────────────────────┬─────────────────────────────────┘
                         │ MCP Call
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 1: Statistical Scorer                   │
│  • Token entropy • Embedding similarity • Poisson rate     │
│  Results: PASS → continue | SUSPICIOUS → escalate         │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 2: Identity Chain Verifier              │
│  • Origin check • Delegation chain • Permission scope      │
│  • Trust decay per hop • Cross-scope trigger               │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 3: Tool Integrity Verifier              │
│  • Manifest hash • Output schema • Registry scan          │
│  • Name collision check • Behavior drift detection        │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 4: Consensus Verifier                   │
│  (Only for high-risk / high-uncertainty actions)           │
│  • Independent agent verification                         │
│  • Byzantine consensus (2-of-3, 3-of-5)                   │
│  • Collusion pattern detection                            │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 5: Sequence Analyzer                    │
│  • N-gram pattern matching • Info flow tracking            │
│  • Gradual escalation detection • Rate anomaly             │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 6: Data Flow Provenance Tracker         │
│  • Taint tracking • Boundary crossing detection            │
│  • Indirect flow analysis • Side channel monitor           │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Layer 7: Behavioral Baseline Anomaly          │
│  • Per-agent baseline • Session comparison                │
│  • Cross-agent comparison • Contextual analysis           │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│              TrustKernel Decision Engine                   │
│  • Bayesian trust update                                  │
│  • ALLOW / HOLD / DENY / QUARANTINE / ESCALATE            │
│  • SQLite audit log                                       │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    Tool / Action                           │
│  (Telegram / Notion / GitHub / DB / File / API)           │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Implementation Priorities

### Phase 0: Pre-Integration Registry Verification (Empirically Required)
*Gap identified by Papers 2 & 4: init-logic attacks execute before any defense, 212 hijackable accounts, 5 leaked tokens*
- **Registry Link Validation**: Verify server links are valid, responsive, and not redirect-hijacked
- **Credential Scanning**: Check for exposed tokens (GitHub PATs, API keys) in config examples
- **Account Ownership Verification**: Check if linked GitHub accounts are active and match claimed maintainer
- **Name Collision Detection**: Levenshtein + embedding scan against known legitimate server names
- **Namespace Integrity Check**: Detect affix-squatting (e.g., `github-mcp` vs `mcp-github`)
- **Init Logic Sandbox**: Execute server init logic in sandboxed environment before permitting integration
- **Tool Metadata Analysis**: Heuristic scan for manipulative descriptions (`<IMPORTANT>`, "BEST tool", attention-drawing labels)

### Phase 1: L1-L3 (Foundation — Current Sprint)
- **L1 Statistical Scorer**: Embedding-based pre-filter using local Ollama model. Train on v5 datasets (jailbreak + gov_bypass + mcp_contamination).
- **L2 Identity Chain**: Cryptographically sign agent IDs at source. Propagate delegation chain. Enforce scope decay.
- **L3 Tool Integrity**: Runtime manifest hash verification. Output schema validation. Name collision detection (Levenshtein + embedding).

### Phase 2: L5-L6 (Pattern Recognition)
- **L5 Sequence Analyzer**: N-gram tool call pattern database. Gradual escalation detector. Rate anomaly detection.
- **L6 Data Flow Provenance**: Taint tracking across tool calls. Boundary crossing detection. Direct output-to-input flow analysis.

### Phase 3: L4 (Multi-Agent)
- **L4 Consensus Verifier**: Independent verification routing. Byzantine consensus. Collusion detection via statistical agreement analysis.

### Phase 4: L7 (Evolution)
- **L7 Behavioral Baseline**: Per-agent behavioral profiles. Session-to-session comparison. Cross-agent correlation analysis.

---

## 6. Testing Against Stress Datasets

The v5 and v6 stress datasets provide 200K+ labeled test cases across all attack types. Testing protocol:

1. Run each attack through the 7-layer stack
2. Record which layers detect/block/miss each attack
3. Calculate per-layer and stack-wide defense rate
4. Iterate on weak layers until stacked defense ≥ 80%
5. Run combined attack scenarios (TAMAS multi-agent kill chains, tool chaining)
6. Red-team the defense itself (can we bypass it?)

### Empirical Baseline (as of 2026-05-20)
| Measurement | Result | Source |
|---|---|---|
| Current governance scoring (keyword-only) | 0.034-0.116 on v5 datasets | `governance_eval_results.json` |
| Paper 2 scanner detection rate (mcp-scan) | 3.3% (4/120) | Zhao et al. empirical eval |
| Paper 2 attack success (6 categories) | 100% ASR across all host-LLM combos | Zhao et al. |
| Paper 4 vulnerable servers | 1.24% (833/67,057) | Li & Gao registry analysis |
| Paper 4 tool poisoning ASR (best case) | 100% (Cursor + Claude/Gemini) | Li & Gao |
| Paper 4 tool poisoning ASR (worst case) | 0% (Cursor + GPT-4o, server tools) | Li & Gao |

### Key Validation Targets
| Target | Baseline | Target | Method |
|---|---|---|---|
| L1 statistical detection (naive attacks) | ~15% keyword-only | ≥60% | Embedding + entropy-based |
| L2 identity verification (spoofing) | 0% (no tracking) | ≥90% | Crypto-signed delegation chains |
| L3 tool integrity (poisoning) | 3.3% (mcp-scan) | ≥70% | Manifest hashing + runtime verification |
| L4 consensus (sophisticated attacks) | 0% (no consensus) | ≥50% | Independent verification |
| L5 sequence (chaining) | 0% (no sequence analysis) | ≥60% | N-gram + escalation detection |
| L6 provenance (data flow) | 0% (no taint tracking) | ≥50% | Cross-tool taint analysis |
| L7 behavioral (zero-day) | 0% (no behavioral model) | ≥40% | Per-agent baseline |
| **Stacked defense (combined)** | ~3-11% | **≥80%** | All layers combined |

---

## 7. Key Design Principles

### Principle 1: No Single Point of Failure
The critical insight from all research papers and stress datasets:

> **No single defense layer can be relied upon. Every layer must assume it will be bypassed by a sufficiently sophisticated attacker. The security comes from the combination.**

- Layer 1 may miss encoding attacks — Layer 7 catches abnormal tool calling patterns
- Layer 2 may miss registry poisoning — Layer 3 verifies runtime integrity
- Layer 5 may miss delayed conditionals — Layer 7 detects behavioral drift
- Layer 6 may miss indirect flows — Layer 4 requires consensus

**The Stack is the defense, not any individual layer.**

### Principle 2: Host Design > Model Capability
Empirically confirmed by Papers 2 & 4:
- **System prompts matter more** than LLM model choice (Paper 2: A4 ASR dropped from 100% to 6.7% by changing system prompt)
- **All tested hosts lack independent verification** of LLM tool selections (Paper 4: Cursor, Windsurf, Claude Desktop, Cline)
- **Safety awareness ≠ safety enforcement**: Gemini 2.5 Pro identifies abnormal instructions but follows them anyway (Paper 4)

**The defense must be host-aware and not assume LLM safety alignment protects MCP calls.**

### Principle 3: Pre-Integration Phase Exists
Paper 2's A3 attacks execute before any runtime defense. Paper 4's registry analysis confirms 833 pre-existing vulnerable servers. **Defense must start before integration, not after.**

### Principle 4: Scanner-Only Defense is Doomed
mcp-scan detected 3.3% of attacks. AI-Infra-Guard costs ~$0.50 + ~10 min per scan. **Real-time static scanning is impractical and ineffective.** Defense must be runtime, layered, and continuous.

---

## 8. Empirical Validation Status (Updated 2026-05-20)

Four new papers provide empirical data that validates and challenges our model's assumptions:

### What Papers Confirm
| Finding | Source | Validation for Our Model |
|---|---|---|
| Tool poisoning is real and effective (up to 100% ASR) | Papers 2, 4 | L3 Tool Integrity is correct priority |
| Registry-level attacks are active threat (212 hijackable accounts, 833 vulnerable servers) | Paper 4 | L2 Identity + L3 verification needed before integration |
| Hosts lack independent verification of LLM tool selections | Paper 4 | L4 Consensus (independent verification) is uniquely valuable |
| No single defense is sufficient (scanners detect 3.3%) | Paper 2 | **Our core thesis confirmed** — stack is the defense |
| System prompts matter more than model capability | Paper 2 | L4 diversity + L7 behavioral baselines are correct approach |
| Keyword-only detection fails (proof: scores ~0.03-0.12 on v5 data) | Our baseline eval | L1 must be statistical, not keyword-based |

### What Papers Challenge
| Finding | Source | Adjustment Needed |
|---|---|---|
| A3 Initialization Logic attacks execute before any defense layer | Paper 2 (100% ASR) | Need pre-integration sandbox (not in current 7-layer model) |
| Gemini 2.5 Pro identifies but follows abnormal instructions | Paper 4 | Safety alignment ≠ safety enforcement — L7 must detect behavioral compliance, not just refusal |
| Host-specific tool confusion bugs (Cursor first-listed tool) | Paper 4 | Need host-aware defense configuration |
| Registry pre-integration vetting not done anywhere | Paper 4 | Missing from current model — add Phase 0: Registry Verification |

### Empirical Attack Success Rates (Paper 2, Zhao et al.)
| Category | Avg ASR | Our Coverage |
|---|---|---|
| Server Metadata Poisoning | 94% | L2, L3 |
| Server Configuration Abuse | 100% | L1, L2 |
| Initialization Logic Attack | 100% | **Gap** — needs sandbox |
| Tool Metadata Poisoning | 89.3% | L3 |
| Tool Logic Attack | 100% | L3, L5 |
| Tool Output Attack | 100% | L5, L6 |
| Resource Metadata Poisoning | 66.7% | L3 |
| Resource Logic Attack | 100% | L3, L5 |
| Resource Output Attack | 67.8% | L5, L6 |
| Prompt Metadata Poisoning | N/A | L1, L7 |
| Prompt Logic Attack | 100% | L1, L5 |
| Prompt Output Attack | 46.7% | L5, L6, L7 |

### Registry Ecosystem Stats (Paper 4, Li & Gao)
| Metric | Value | Threat Vector |
|---|---|---|
| Servers analyzed | 67,057 across 6 registries | N/A |
| Code-vulnerable servers (MCPInspect) | 833 (1.24%) | Exploitation |
| Suspicious tool descriptions | 18 | Tool poisoning |
| Valid GitHub tokens leaked on mcp.so | 5 | Credential theft |
| Maintainer-hijackable accounts | 212 (15.37%) | Supply chain |
| Redirect-hijackable accounts | 304 | Supply chain |
| Affix-squatting name groups (npm) | 408 groups, 80.6% different maintainers | Server impersonation |

---

## 9. Key Papers Informing This Model

| Paper | Key Contribution | How It Shaped This Model |
|---|---|---|
| arXiv 2504.08623 (Enterprise MCP Security — AWS/Intuit) | MAESTRO 7-layer framework, Zero Trust patterns, defense-in-depth for MCP | Enterprise mitigation controls, OAuth/JIT patterns, output filtering |
| arXiv 2509.24272 (When MCP Servers Attack — NUS/PKU) | 12-category component-based attack taxonomy, cross-host/LLM ASR, scanner effectiveness eval, 1M+ server generator | Confirmed stack defense necessity, empirical ASR baselines, stakeholder responsibility framework |
| arXiv 2503.23278 (MCP Threat Landscape — HUST) | 4 lifecycle phases, 16 activities, 4 attacker types, 16 threat scenarios, 26 collections catalogued | Full 7-layer architecture, lifecycle-aware defense placement |
| arXiv 2510.16558 (MCP Security Issues — UDelaware, DSN 2026) | 67K server registry analysis, two-stage attack surface, MCPInspect tool, 833 vulnerable servers, 212 hijackable accounts | Registry-level vetting (Phase 0), host-independent verification, credential scanning |
| INJECAGENT (Indirect Prompt Injection) | Cross-context injection taxonomy | L6 Data flow provenance |
| TAMAS (Multi-Agent Attacks) | 7 attack types, 3 topologies, 12 scenarios | L4 Consensus + L5 Sequence |
| SKILL-IECT (Skill File Attacks) | Skill file as attack vector | L3 Integrity + L6 Flow |
| GPTFUZZER | Automated red teaming framework | Testing methodology |
| JailbreakZoo (1405 techniques, 11 families) | Comprehensive jailbreak taxonomy | L1 Statistical + L7 Baseline |
| MirrorShield | Universal defense via reflection | L7 Behavioral baseline |
| Lockpicking-LLMs (Logit-based jailbreak) | Token-level manipulation | L1 Token distribution entropy |
| Trojans Whisper (OpenClaw manipulation) | Stealthy compromise of agent frameworks | L6 Data flow + L7 Baseline |
