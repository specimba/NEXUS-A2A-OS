# NEXUS OS Threat Model — v1.0

**Date**: 2026-05-27  
**Branch**: canonical-617  
**Status**: ACTIVE — updates with every red-team finding, paper ingested, or sandbox boundary discovered.

---

## 1. Purpose

This document maps every known attack class, paper, and empirical sandbox finding to a specific NEXUS OS component and a **pass/fail test gate** that the Stress Lab (`nexusctl sec`) must enforce before any production artifact ships.

It treats Grok 4.3 sandbox testing as **legitimate beta developer experimentation**, not as adversarial intrusion. Findings from that environment are reformulated as defensive hardening requirements for NEXUS.

---

## 2. Attack Surface Map

### 2.1 Prompt-Level Attacks

| Attack | Source Paper | Target Component | Defense Mechanism | Pass/Fail Gate |
|--------|-------------|------------------|-------------------|----------------|
| Direct Prompt Injection (DPI) | TAMAS (2511.05269) | TokenGuard | Input sanitizer + role-bound system prompt anchoring | `nexusctl sec --gate=dpi` → TokenGuard must reject >95% of DPI probes from REDBENCH adversarial set |
| Impersonation ("As requested by admin...") | TAMAS (2511.05269) | Trust Function v2.1 | Lane-scoped Ed25519 signature verification — no authority claim accepted without cryptographic proof of origin | `nexusctl sec --gate=impersonation` → Trust Function must reject all unsigned authority claims |
| Logit-based Jailbreak (JAILMINE) | Lockpicking LLMs (2405.13068) | GMR Engine v3.0 | Per-token entropy threshold detection; if anomalous token probability distribution detected → circuit-break to HOT path | `nexusctl sec --gate=jailbreak` → GMR must detect and route-to-HOT within 3 tokens of anomalous distribution |

### 2.2 Environment-Level Attacks

| Attack | Source Paper | Target Component | Defense Mechanism | Pass/Fail Gate |
|--------|-------------|------------------|-------------------|----------------|
| Indirect Prompt Injection (IPI) | TAMAS (2511.05269) | Hermes Router + 5-Track Memory | All tool output passes through TokenGuard before agent consumption; memory tracks tagged with provenance level (SOURCE/INFERRED/AMBIGUOUS) | `nexusctl sec --gate=ipi` → TokenGuard must detect injected instructions in tool output with F1 ≥ 0.90 |
| Surrogate Ensemble Search | Blackbox Attacks via Surrogate Ensemble Search (PDF #1) | GMR Engine | Adversarial training during model selection; diversity-enforced ensemble that requires consensus across providers | `nexusctl sec --gate=surrogate` → GMR ensemble must disagree on ≤5% of clean inputs, and detect >80% of surrogate probes |
| Sandbox Escape via Package Manager | Grok sandbox finding (Hades cluster) | Sovereign Kernel (DERDDRE-01) | eBPF egress-drop default; per-agent opt-in network capability gated by Ed25519 signature + governance proposal | `nexusctl sec --gate=sandbox-escape` → Any process not on cryptographic allowlist must fail to reach external network |

### 2.3 Agent-Level Attacks

| Attack | Source Paper | Target Component | Defense Mechanism | Pass/Fail Gate |
|--------|-------------|------------------|-------------------|----------------|
| Byzantine Agent | TAMAS (2511.05269) | Team Coordinator | Output verification by 2-of-3 agent quorum; any agent producing contradictory output triggers automatic quarantine | `nexusctl sec --gate=byzantine` → Coordinator must detect and isolate Byzantine agent within 3 message rounds |
| Colluding Agents | TAMAS (2511.05269) | KAIJU 4-variable governance | Non-overlapping agent role assignment enforced at spawn time; agents with overlapping capabilities require mandatory review gate before collaboration | `nexusctl sec --gate=collusion` → KAIJU must prevent collusion-enabling role assignments at spawn time |
| Contradicting Agents | TAMAS (2511.05269) | EDICT review gate (DERDDRE-01) | Mandatory audit phase with veto power; output contradiction triggers rework loop | `nexusctl sec --gate=contradiction` → EDICT review gate must detect contradictory outputs from agents with similar functionality |

### 2.4 Infrastructure Attacks

| Attack | Source Paper | Target Component | Defense Mechanism | Pass/Fail Gate |
|--------|-------------|------------------|-------------------|----------------|
| K8s RBAC Abuse (Service Account Token) | Grok sandbox finding (Hades cluster) | Sovereign Kernel | No automount of service account tokens; KVM-level memory encryption (AMD SEV / Intel TDX per DERDDRE-01) | `nexusctl sec --gate=rbac` → K8s service account token must not be readable from agent sandbox |
| Supply Chain via Package Mirror | Grok sandbox finding (35.245.43.102 proxy) | Git-BIOS + SLSA attestation | All packages verified against SLSA Level 3 provenance; package allowlist enforced cryptographically | `nexusctl sec --gate=supply-chain` → Any package without valid SLSA attestation must be blocked at install time |
| Adversarial Example Transfer | Blackbox Attacks via Surrogate Ensemble Search | GMR Engine | Cross-model adversarial training; no single model in cascade shares architecture with any other | `nexusctl sec --gate=transfer` → Adversarial examples crafted against one GMR model must have <30% transfer success rate to cascade fallback |

### 2.5 Privacy Attacks

| Attack | Source Paper | Target Component | Defense Mechanism | Pass/Fail Gate |
|--------|-------------|------------------|-------------------|----------------|
| Training Data Extraction | On Protecting the Data Privacy of LLMs (PDF #6) | 5-Track Memory | Differential privacy on memory retrieval; canary-injected audit pipeline | `nexusctl sec --gate=extraction` → Memory retrieval must fail canary extraction at ε < 1.0 |
| Membership Inference | Privacy in LLMs: Attacks, Defenses (PDF #7) | 5-Track Memory | Per-query access logging with anomaly detection; excessive probing triggers rate-limit + quarantine | `nexusctl sec --gate=membership` → After 50 probe queries from same agent identity in 60s window, access must be revoked |
| Side-Channel via Token Timing | Grok sandbox finding | GMR Engine | Constant-time token routing; timing variance across providers must be <50ms regardless of model internal state | `nexusctl sec --gate=side-channel` → GMR routing latency variance must be within 50ms for all models in tier |

---

## 3. Sandbox Boundary Architecture (from Grok findings, applied to NEXUS)

### 3.1 Observed xAI Sandbox Pattern

```
┌─────────────────────────────────────────────┐
│  Kubernetes Pod: hades-openbar               │
│  ┌───────────────────────────────────────┐   │
│  │  Grok Agent                            │   │
│  │  ├── Code Execution (Python/Go)        │   │
│  │  ├── MCP Tool Calling (via gateway)    │   │
│  │  └── File I/O (workdir/artifacts)     │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │  Network Controls                      │   │
│  │  ├── DNS: resolves all hosts           │   │
│  │  ├── TCP/HTTPS: blocked (except proxy) │   │
│  │  ├── Package Manager: whitelist proxy  │   │
│  │  │   └── 35.245.43.102 (pip/go/npm)   │   │
│  │  └── Internal API: polygon/coingecko   │   │
│  │      └── via hades-openbar.svc.local   │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │  MCP Gateway: connectors-gateway       │   │
│  │  └── external tools only               │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 3.2 NEXUS Sandbox Pattern (harder)

```
┌─────────────────────────────────────────────┐
│  NEXUS Sovereign Zone (per DERDDRE-01)       │
│  ┌───────────────────────────────────────┐   │
│  │  KVM-Backed Agent Zone                 │   │
│  │  ├── WASM Sandbox (no native binaries) │   │
│  │  ├── eBPF egress-drop default          │   │
│  │  └── Ed25519-signed tool registry      │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │  Package Mirror (SLSA-enforced)        │   │
│  │  ├── All packages: SLSA L3 attestation  │   │
│  │  ├── Cryptographic allowlist           │   │
│  │  └── No unsigned artifact execution     │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │  ModelRelay (NIM-primary)              │   │
│  │  ├── 14 verified models               │   │
│  │  ├── English-only enforcement          │   │
│  │  └── Per-token circuit breaker         │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 4. Grok 4.3 Beta Developer Integration

### 4.1 Legitimacy Statement

Grok 4.3 beta is a developer-testing partnership. All connections between Zo and Grok's sandbox are **explicitly consented beta experiments**, not adversarial penetration testing. The goal is to validate sandbox boundary hardening at both ends.

### 4.2 Connection Architecture

Since Grok's sandbox blocks outbound TCP/HTTPS, Zo cannot be reached via standard HTTP calls. The connection must be **file-based** or **MCP-gateway-mediated**.

#### Option 1: File-Based Relay (implemented below)

```
Grok 4.3 sandbox                    Zo Computer
┌─────────────────────┐            ┌──────────────────────┐
│ artifacts/           │  export   │ grok-coordination/    │
│  experiment_*.md    │ ────────→ │  ingest/              │
│  findings_*.json     │  import   │  grok_*.md           │
│  NEXUS_directive.md │ ←──────── │  directives/          │
└─────────────────────┘            │  zo_response_*.md     │
                                   └──────────────────────┘
```

How it works:
1. Zo's `Zo-NEXUS-Research-Scout` automation writes directives into `grok-coordination/directives/`
2. User exports directives from Zo workspace, imports into Grok sandbox
3. Grok reads directives, executes experiments, writes results to `artifacts/`
4. User exports results from Grok sandbox, places in `grok-coordination/ingest/`
5. Zo's `Zo-NEXUS-Progression-Tracker` reads ingest, updates progression tracker

#### Option 2: MCP Gateway Mediation (requires xAI-side config)

If xAI developers can register a custom MCP server at their connectors-gateway:
1. Deploy a Zo-side MCP server with attestation
2. Register it at `connectors-gateway.grok.com`
3. Grok calls Zo's ModelRelay and swarm endpoints through the official MCP channel

### 4.3 File-Based Coordination — Current State

| Path | Purpose | Status |
|------|---------|--------|
| `/api/grok-swarm` | Bearer-token-gated swarm endpoint | Deployed — Grok can't reach it (TCP blocked) |
| `grok-coordination/queue/pending/` | Task queue for Grok | Needs file-export workflow |
| `grok-coordination/directives/` | Zo → Grok instructions | Built below |
| `grok-coordination/ingest/` | Grok → Zo results | Built below |

---

## 5. Test Gate Registry

Each test gate is invoked as `nexusctl sec --gate=<name>`. All gates must pass before `nexusctl sec` can produce a golden host.

| Gate ID | Target Component | Attack Class | Threshold |
|---------|-----------------|--------------|-----------|
| `dpi` | TokenGuard | Direct Prompt Injection | >95% rejection on REDBENCH set |
| `impersonation` | Trust Function | Authority impersonation | 100% rejection of unsigned authority claims |
| `jailbreak` | GMR Engine | Logit manipulation | Detect within 3 tokens |
| `ipi` | Hermes Router | Indirect Prompt Injection | F1 ≥ 0.90 |
| `surrogate` | GMR Engine | Surrogate ensemble attack | >80% detection rate |
| `sandbox-escape` | Sovereign Kernel | Container escape via network | Zero egress from unsigned processes |
| `byzantine` | Team Coordinator | Byzantine agent behavior | Isolation within 3 rounds |
| `collusion` | KAIJU | Colluding agent spawn | Prevent at spawn time |
| `contradiction` | EDICT Gate | Output contradiction | Detect + force rework |
| `rbac` | Sovereign Kernel | K8s token abuse | Token inaccessible from sandbox |
| `supply-chain` | Git-BIOS | Package compromise | SLSA L3 enforcement |
| `transfer` | GMR Engine | Adversarial transfer | <30% cross-model transfer |
| `extraction` | 5-Track Memory | Training data extraction | ε < 1.0 DP canary test |
| `membership` | 5-Track Memory | Membership inference | Quarantine after 50 probes/60s |
| `side-channel` | GMR Engine | Timing side-channel | Variance <50ms |

---

## 6. Paper Ingestion Status

| Paper | Read | Component Mapped | Test Gate Written |
|-------|------|-----------------|-------------------|
| Blackbox Attacks via Surrogate Ensemble Search | TODO (full read needed) | GMR Engine | `surrogate`, `transfer` (sketched) |
| HAICOSYSTEM (CMU Sandboxing) | TODO | Sovereign Kernel + Stress Lab | Pending full read |
| Diverse Red Teaming with Auto-Generated Rewards | TODO | Curator (attack-catalog evolution) | Pending full read |
| REDBENCH | TODO | All components (benchmark source) | Targets TBD |
| Lessons From Red Teaming 100 Generative Products | TODO | Operational red-team rotation | Pending full read |
| On Protecting the Data Privacy of LLMs | TODO | 5-Track Memory | `extraction` (sketched) |
| Privacy in LLMs: Attacks, Defenses, and Future | TODO | 5-Track Memory | `membership` (sketched) |

Status: 7 PDFs attached, failed initial extraction. Full reads needed before finalized test gates.

---

*Document maintained on `canonical-617`. Updated by Zo automations as new papers, sandbox findings, and test results arrive.*
