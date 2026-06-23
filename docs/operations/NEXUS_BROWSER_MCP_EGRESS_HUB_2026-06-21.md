# NEXUS Browser MCP Egress Hub - 2026-06-21

## Purpose

Create a governed custom-MCP connector path for Grok, GPT browser sources, and similar browser-sandbox AIs. The goal is to give those systems bounded internet/evidence capability and NEXUS task handoff, not raw local filesystem access, token access, shell access, or unrestricted proxy behavior.

## Grounding Matrix

| Evidence | Finding | NEXUS decision |
|---|---|---|
| MCP 2025-06-18 transport spec | Streamable HTTP is current; older HTTP+SSE remains a compatibility path. The spec requires Origin validation, localhost binding for local servers, and proper auth for HTTP transports. | Keep `/sse` for Grok compatibility, but design the next bridge around a single `/mcp` Streamable HTTP endpoint plus legacy `/sse`. |
| MCP authorization spec | HTTP MCP authorization is OAuth-oriented, with protected resource metadata and bearer-token validation as the real long-term route. | Do not treat a random ngrok URL as authentication. Add connector identity, tunnel secret, and future OAuth/protected-resource metadata. |
| SMCP paper | Secure MCP needs identity, mutual authentication, security-context propagation, fine-grained policy, and audit logging. | Every browser-AI tool call must carry source, lane, tool, decision, and audit hash. |
| Attested Tool-Server Admission | MCP hosts normally trust self-declared tool lists too much; the paper proposes signed clearance, deny-by-default per-server allowlists, and tamper-evident audit. | Public connector must expose a curated façade, not the whole internal NEXUS/GROSS tool registry. |
| MCP tool-poisoning threat model | Tool metadata and parameter visibility are client-side weak points. | Tool descriptions must be short, literal, and non-instructional; no hidden directives or broad “do anything” language. |
| `D:\GROSS\grok_mcp_server.py` | Original Grok-facing FastMCP SSE server exposes 22 tools including `http_diagnostic`, A2A, audit, evidence, coordination queue, and health. | Treat as upstream evidence/source. Use the NEXUS-owned hardened clone at `tools/browser_ai_mcp/grok_mcp_server_v2.py` for connector testing and public tunnel work. |
| `nexus_os/bridge/browser_http_diagnostic.py` | NEXUS relay validates HTTPS, GET/HEAD, private-target blocking, allowlisted hosts, and strips sensitive headers before calling GROSS. | Use this as the canonical local policy engine for HTTP egress preparation and live calls. |
| `nexus_os/mcp/bridge_server.py` | NEXUS MCP bridge already gates `/invoke` with `transport_validator` and `MCPGuard`. | Keep NEXUS governance MCP separate from public browser-AI connector until a façade layer is implemented. |

Actionable insight: the next useful move is a **NEXUS Browser MCP Egress Hub façade**: narrow tools, source identity, auditable HTTP diagnostics, task-envelope handoff, and no direct access to raw GROSS/NEXUS internals.

## Canonical Ports

| Port | Owner | Browser-AI role |
|---:|---|---|
| 7352 | Brain API / NEXUS governance only | Never expose directly through Grok/GPT custom MCP. |
| 7354 | GROSS MCP bridge | Local SSE/A2A bridge behind tunnel. |
| 7355 | Python ModelRelay fallback/internal | Not exposed to browser AI. |
| 7356 | Static dashboard | Optional read-only dashboard preview. |
| 7357 | God-mode proxy | Not exposed to browser AI. |

## Connector Profiles

### Profile A - Current Grok Compatibility

- Local: `http://127.0.0.1:7354/sse`
- Public: `https://<tunnel-domain>/sse`
- Tool source: `tools/browser_ai_mcp/grok_mcp_server_v2.py` hardened NEXUS clone
- Use when Grok custom connector only accepts SSE.
- Required local preflight:
  - `nexusctl gross-http https://huggingface.co --method HEAD --operator codex --audit-id preflight`
  - `Invoke-WebRequest http://127.0.0.1:7354/health -UseBasicParsing`
  - Tunnel health check for `https://<tunnel-domain>/health`

### Profile B - NEXUS Governed HTTP Egress

- Local policy: `nexus_os.bridge.browser_http_diagnostic.BrowserHTTPDiagnosticRelay`
- CLI: `nexusctl gross-http <https-url> --method GET|HEAD`
- Default allowed hosts: Hugging Face, GitHub raw, PyPI, Grok file hosts.
- Expand host reach per run with:
  - `NEXUS_BROWSER_HTTP_ALLOWED_HOSTS=modelcontextprotocol.io,arxiv.org,huggingface.co,github.com,raw.githubusercontent.com`
- This does not disable HTTPS, GET/HEAD, private-IP blocking, or sensitive-header stripping.

### Profile C - Future Streamable HTTP MCP

- Local endpoint: `http://127.0.0.1:7354/mcp`
- Public endpoint: `https://<stable-domain>/mcp`
- Use after bridge supports MCP 2025-06-18 Streamable HTTP.
- Keep `/sse` as compatibility until Grok/GPT both accept `/mcp`.

## Public Tool Façade

Expose these tools to Grok/GPT first:

| Tool | Purpose | Writes? | Notes |
|---|---|---:|---|
| `ping` | Connector health | No | Always safe. |
| `registry_debug` | Tool/version fingerprint | No | Must not expose local paths beyond bridge category. |
| `http_diagnostic` | Bounded HTTPS GET/HEAD evidence | No | Use allowlist, no auth headers, max preview, audit hash. |
| `task_add` | Add governed task proposal | Queue write | Only accepts dry-run `NexusClawTaskEnvelope`; no shell commands. |
| `task_list` | View pending/done/failed queue counts | No | Limit returned bodies. |
| `task_complete` | Record external advisory artifact | Queue write | Result must include artifact hash and local verification instructions. |
| `agent_publish_message` | Advisory A2A channel post | Queue write | Only for `advisory/*` topics; no credentials or raw logs. |
| `agent_retrieve_messages` | Read advisory channel tail | No | Return last N, capped. |

Do not expose these to public browser-AI connectors until separately reviewed:

- Any raw filesystem read/write.
- Any shell, subprocess, code execution, browser-cookie, or credential tool.
- Any GROSS raw evidence dump/export tool.
- Any delete/purge/remediation tool.
- Any tool that accepts arbitrary POST targets or forwards arbitrary headers.

## Hardened NEXUS Clone Status

The NEXUS-owned clone at `tools/browser_ai_mcp/grok_mcp_server_v2.py` now implements the bridge hardening required for controlled connector use:

1. Strips sensitive headers server-side: `Authorization`, `Cookie`, `Proxy-Authorization`, `X-API-Key`, `X-Auth-Token`, CSRF/XSRF headers.
2. Blocks private, loopback, link-local, multicast, and metadata IP targets.
3. Enforces `GROK_HTTP_ALLOWED_HOSTS` host allowlist.
4. Caps response body reads and safe previews.
5. Does not follow redirects; 3xx is returned as evidence with `redirect_location`.
6. Exposes `/health` with tool count, hardening policy, and runtime-write fallback status.
7. Keeps `D:\GROSS` as primary runtime storage when writable, but falls back to repo-local `scratch/browser_ai_mcp_runtime` instead of failing A2A/MCP calls.

Original `D:\GROSS\grok_mcp_server.py` should remain evidence/upstream until the same patch is deliberately ported there. Public Grok/GPT custom connector testing should point at the cloned v2 bridge, not Brain API `7352` and not raw ModelRelay.

## Grok/GPT Long-Run Prompt Contract

Use this prompt pattern after connector health passes:

```text
You have access to the NEXUS browser MCP connector. Use it as a governed evidence and task-handoff bridge, not as a shell or unrestricted proxy.

Mission:
1. Use `ping` and `registry_debug` first. Report server version, tool count, registry hash.
2. Use `http_diagnostic` only for HTTPS GET/HEAD on the named public sources. Do not request cookies, tokens, private IPs, localhost, or credential headers.
3. For each source, return status_code, final_url, content_type, response_length_bytes, body_sha256, and at most 5 evidence observations.
4. If you need local NEXUS work, create a dry-run `task_add` proposal with: task_id, lane, intent, risk_level, required_capabilities, egress_policy, evidence_refs, local verification commands, and stop rules.
5. Do not claim completion until you provide artifact hashes and local verification instructions.
6. If a tool fails, call `task_add` with a failure-analysis task instead of retrying blindly.
```

## Automation Rule

Only one browser-AI supervisor automation should control this lane. It must:

1. Read its memory before doing browser or MCP work.
2. Cheap-check connector health first.
3. Run one bounded prompt only if prior state says work is pending or failed with a new hypothesis.
4. Save memory at the end with: source URL, prompt hash, connector fingerprint, artifact names, local verification status, blocker, and next exact prompt.
5. Return `DONT_NOTIFY` only after a successful baseline exists and nothing changed.

## Stop Rules

Stop and notify if:

- Tunnel URL changed and connector is not reconfigured.
- `/health` is unreachable locally or publicly.
- Tool count/hash changes unexpectedly.
- `http_diagnostic` can reach private IP/localhost/metadata services.
- Any tool asks for cookies, tokens, local files, shell, deletion, or raw GROSS evidence.
- More than one automation is trying to operate the same Grok/GPT conversation.

## Local Verification Commands

```powershell
python -m pytest tests\tools\test_grok_mcp_server_v2_static.py tests\bridge\test_browser_http_diagnostic.py -q --tb=short
nexusctl gross-http https://huggingface.co --method HEAD --audit-id browser-mcp-preflight --operator codex
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7354/health | Select-Object -ExpandProperty Content
```

## Adoption Gate

This plan is ready for controlled use when:

- Focused bridge tests pass.
- GROSS `/health` reports expected tool count and registry hash.
- Public tunnel `/health` matches local health.
- A single Grok or GPT run returns a task proposal and no raw local data.
- The next automation reads/writes memory and does not spawn duplicate conversations.

