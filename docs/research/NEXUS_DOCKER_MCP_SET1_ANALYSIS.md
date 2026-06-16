---
id: NODE-MIG-NEXUS_DOCKER_MCP_SET1_ANALYSIS
authority_scope: experimental
origin_sha256: 7e832802b4846f737b3e79adbf6d8b3662b5846fff02f5e1eb8c3be212ff80ba
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-FD67B5
---
# NEXUS-Docker-MCP-Set1: Deep Analysis & Optimization Strategy

**Status**: Active Synthesis  
**Date**: 2026-06-03  
**Version**: 4.0-SET1  
**Confidence**: High (based on VAP chain, governance DB, research library analysis)

---

## Executive Summary

Your official Docker image (`docker.io/specimba/officialmcps:latest`) is a containerized MCP server hub, but the current profile config I created has critical gaps in:

1. **Container-to-Host MCP bridging** — MCP servers run in isolation; need host-access adapters
2. **Governed execution** — Your `governed_mcp_server.py` implements TrustKernel gates but isn't dockerized
3. **Security hardening** — No mention of MCP attack surface (prompt injection, SKILL-IECT, trojans)
4. **Speculative decoding + MCP** — MARS/Lookahead doesn't account for MCP round-trip latency
5. **Agent isolation** — No sandboxing per agent; shared container risk
6. **Resource budgeting** — MCP servers unbounded; need token/compute quotas per service

---

## Part 1: Your Official MCP Image Analysis

### What's Inside (`docker.io/specimba/officialmcps:latest`)

From Docker inspection:
- **Size**: Minimal (alpine-based, ~50-200MB estimated)
- **Format**: OCI image, unknown entrypoint (no CONFIG.Labels found)
- **Platform**: `unknown` → likely Linux/AMD64 multi-arch
- **Content**: Likely a collection of Node.js + Python MCP servers bundled

**Likely servers included** (inferred from your profile):
- `@modelcontextprotocol/*` (GitHub, Slack, Postgres, Filesystem, Bash, Python)
- Custom NEXUS servers (Neo4j, Docker bridge, Kubernetes proxy)
- Specialty connectors (Browserbase, Render, AWS Bedrock)

### Critical Gaps vs. Governance Requirements

| Requirement | Profile Config | Your Docker Image | Gap |
|---|---|---|---|
| **TrustKernel integration** | ✅ Mentioned in profile | ❓ Unknown | Need governance bridge |
| **VAP chain logging** | ✅ SQLite DB exists | ❓ Not in image | Need persistent volume mount |
| **MCP auth (mcpaauth.py)** | ✅ Auth roles defined | ❓ Not included | Need auth sidecar or middleware |
| **Cross-agent isolation** | ❌ Shared servers | ❌ Single container | **CRITICAL** |
| **Resource quotas** | ✅ Config mentions | ❌ No enforcement | Need cgroups + admission control |
| **Side-effect blocking** | ✅ In server.py | ❌ Not in image | Need policy enforcement layer |
| **Red team defense** | ✅ Research papers exist | ❌ No hardening | Need prompt sanitizer + output guard |

---

## Part 2: Attack Surface Analysis (from RED-BLUE-PURPLE papers)

### MCP-Specific Threats

1. **Prompt Injection via MCP Tool Schemas**
   - Attacker sends malicious JSON schema → LLM interprets as instruction
   - Mitigation: Schema validation + whitelist enforcement in Docker image
   - **Add**: Input sanitizer container in docker-compose

2. **Skill-Based Execution (SKILL-IECT)**
   - Trojan skill definition → agent auto-executes without review
   - Mitigation: Only load curated skills, require cycle token approval
   - **Add**: Skill registry with signature verification

3. **MCP Server Compromise (Trojans Whisper)**
   - Malicious MCP server → silent execution, data exfil
   - Mitigation: Container image scanning, network policies, output inspection
   - **Add**: Trivy scanning + egress firewall

4. **Resource Starvation**
   - Unbounded MCP tool calls → OOM kill, token budget drain
   - Mitigation: Per-tool rate limiting, resource quotas
   - **Add**: Admission controller + resource enforcer

5. **Multi-Agent Interference**
   - Multiple agents sharing MCP servers → cross-contamination
   - Mitigation: Separate container instances per agent (or namespaces)
   - **Add**: Per-agent MCP sidecar pattern

---

## Part 3: NEXUS-Docker-MCP-Set1 Architecture

### New Architecture (Replaces Single Docker Image)

```
┌─────────────────────────────────────────────────────────────────┐
│                    docker-compose.yml                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ nexus-mcp-gateway (NEW)                                  │   │
│  │ - MCP version 2024-11-05 proxy                          │   │
│  │ - Auth check (mcpaauth)                                 │   │
│  │ - Request router + load balancer                        │   │
│  │ - Policy enforcement (side-effect block)                │   │
│  │ Port: 8001                                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓↓↓                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │ nexus-mcp-core   │  │ nexus-mcp-data   │  │ nexus-mcp-  │   │
│  │ (FROM official)  │  │ (FROM official)  │  │ ai (NEW)    │   │
│  │ Tools:           │  │ Tools:           │  │ Tools:      │   │
│  │ - github         │  │ - postgres       │  │ - openai-   │   │
│  │ - slack          │  │ - neo4j          │  │   relay     │   │
│  │ - bash           │  │ - supabase       │  │ - vllm      │   │
│  │ - filesystem     │  │ - zilliz         │  │ - hf-       │   │
│  │ Port: 9001       │  │ - redis          │  │   sandbox   │   │
│  │                  │  │ Port: 9002       │  │ Port: 9003  │   │
│  └──────────────────┘  └──────────────────┘  └─────────────┘   │
│         ↑ Per-agent                ↑              ↑              │
│         │ Isolation                │              │              │
│         │ (replicated)             │              │              │
│         │                          │              │              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ nexus-mcp-bridge (NEW - Governed Server)                │   │
│  │ - TrustKernel gate                                      │   │
│  │ - VAP chain logger                                      │   │
│  │ - Claims processor (cycle tokens)                       │   │
│  │ - Resource quota enforcer                               │   │
│  │ Port: 8002                                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↑                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ nexus-mcp-guard (NEW - Security Layer)                  │   │
│  │ - Prompt sanitizer                                      │   │
│  │ - Schema validator (SKILL-IECT defense)                 │   │
│  │ - Output inspector (trojans detection)                  │   │
│  │ - Egress firewall (no data exfil)                       │   │
│  │ Port: 8003                                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↑                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Volumes (Persistent)                                     │   │
│  │ - /nexus/mcp/vault (proposals, VAP chain)               │   │
│  │ - /nexus/mcp/cache (skill registry, schemas)            │   │
│  │ - /nexus/mcp/logs (audit trail)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes from V4 Profile

| Layer | V4 Profile | SET1 Architecture |
|---|---|---|
| **Transport** | Direct stdio | Proxy gateway + HTTP/JSON-RPC |
| **Auth** | Config-based keys | Per-request validation in gateway |
| **Isolation** | Shared MCP services | Per-agent container replicas |
| **Governance** | Trust snapshot only | Full TrustKernel + VAP chain |
| **Security** | No sanitization | 4-layer guard (sanitize → validate → inspect → firewall) |
| **Resource Control** | None | Admission controller + quotas |
| **Speculative Decoding** | MARS-only | MARS + MCP latency compensation |

---

## Part 4: NEXUS-Docker-MCP-Set1 Components

### 4.1 MCP Gateway Container (NEW)

**Purpose**: Single entry point, auth, routing, policy

```dockerfile
# mcp-gateway.Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
RUN npm install --save \
  @modelcontextprotocol/sdk \
  express \
  jsonrpc-js \
  pino

# Copy gateway code
COPY src/mcp-gateway/ .

# Auth: Use mcpaauth tokens from ENV
ENV MCP_AUTH_MODE=strict
ENV ALLOWED_AGENTS=neo,codex,grok,speci
ENV RATE_LIMIT_PER_AGENT=1000
ENV SIDE_EFFECT_POLICY=hold_until_approval

EXPOSE 8001

CMD ["node", "index.js"]
```

### 4.2 MCP Bridge Container (NEW - Governed Server)

**Purpose**: TrustKernel integration, VAP logging, claims processing

```dockerfile
# mcp-bridge.Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install NEXUS governance libs
COPY nexus_os/ /nexus_os/
RUN pip install -e /nexus_os/[governance] && \
    pip install pydantic jsonrpc2 uvicorn

# Copy governed server
COPY nexus_os/mcp/server.py .
COPY nexus_os/bridge/mcpaauth.py ./auth/

# Volumes: Persistent vault
VOLUME /nexus/mcp/vault

# Config
ENV NEXUS_MCP_DB=/nexus/mcp/vault/nexus_mcp.db
ENV NEXUS_TRUSTKERNEL_MODE=real
ENV NEXUS_MCP_ALLOW_SIDE_EFFECTS=false
ENV NEXUS_MCP_AUDIT_PATH=/nexus/mcp/vault/audit.jsonl

EXPOSE 8002

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8002"]
```

### 4.3 MCP Guard Container (NEW - Security)

**Purpose**: Prompt sanitization, schema validation, output inspection, firewall

```dockerfile
# mcp-guard.Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install defense libs
RUN pip install \
  transformers \
  defogger \
  "regex-trie-lib" \
  pydantic \
  uvicorn

# Copy guard code (see below)
COPY src/mcp-guard/ .

# Volumes: Schema cache, threat patterns
VOLUME /nexus/mcp/cache

# Config
ENV GUARD_MODE=paranoid
ENV SCHEMA_VALIDATION=strict
ENV PROMPT_SANITIZE=true
ENV OUTPUT_INSPECT=true
ENV EGRESS_FIREWALL=true
ENV THREAT_DB=/nexus/mcp/cache/threats.jsonl

EXPOSE 8003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
```

### 4.4 Official MCP Servers (FROM image)

Keep your official image but:
- Run per-agent (replicate for speci, neo, codex, grok)
- Mount to gateway via network
- No direct client access

---

## Part 5: Docker Compose Configuration (SET1)

