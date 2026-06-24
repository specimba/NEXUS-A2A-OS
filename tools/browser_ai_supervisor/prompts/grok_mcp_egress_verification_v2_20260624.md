NEXUS / Grok MCP egress verification task.

Local Codex state, verified 2026-06-24:
- NEXUS implemented a real local `nexus_os.mcp.egress_governor.McpEgressGovernor`.
- `BrowserHTTPDiagnosticRelay.execute_governed(...)` now exists and defaults to dry-run.
- Focused local tests pass: `27 passed` for MCP egress governor, browser HTTP diagnostic relay, and external browser-AI director tests.
- Live local director proof: authenticated Grok CDP on port 9224 + local GROSS/NEXUS bridge 7354 produced `HEAD https://huggingface.co -> status_code 200, access_result allowed`.
- Treat this as local evidence, not as your own completion claim.

Your job now is to verify the Grok-side connector reality, not to write another plan.

Use only visible/available Grok connected tools or MCP connector tools. Do not ask for secrets. Do not browse private/local files. Do not claim you changed local NEXUS code.

Required tool sequence if available:
1. Call connector health equivalent: `ping` or nearest available tool.
2. Call registry/tool listing equivalent: `registry_debug` or nearest available tool.
3. Call bounded public HTTP evidence tool: `http_diagnostic` or nearest available tool with `HEAD https://huggingface.co`.
4. If one of those tools is not visible, state `BLOCKED_TOOL_NOT_VISIBLE` and list the exact visible connector/tool names you can see.

Return exactly one artifact named:
`GrokMcpEgressIntegrationReport_v2`

Artifact contract:
- `connector_status`: OK/BLOCKED/ERROR
- `visible_tools`: exact tool names observed
- `health_result`: status, version/tool_count/hash if visible
- `http_diagnostic_result`: url, method, status_code, access_result, content_type if visible, body_sha256 if visible
- `delta_vs_local_codex`: what your Grok-side connector proves beyond Codex local proof
- `next_nexus_task_envelope`: one dry-run NexusClawTaskEnvelope proposal only if a real blocker or next local patch exists
- `do_not_execute_notes`: no shell, no credentials, no private URLs, no raw GROSS evidence, no local filesystem access

Stop after the artifact. No motivational prose. No duplicate summary. No fabricated tool outputs.
