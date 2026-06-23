Continue the NEXUS Grok MCP/HTTP egress integration as a real long-run implementation director cycle.

Verified local context from Codex on 2026-06-21:
- NEXUS-owned hardened bridge clone exists at tools/browser_ai_mcp/grok_mcp_server_v2.py.
- Local health is live: http://127.0.0.1:7354/health.
- Version: 2.2.0-nexus-hardened.
- MCP tool count: 22.
- A2A send endpoint: http://127.0.0.1:7354/a2a/tasks/send.
- Runtime write policy: D:/GROSS primary, repo-local scratch/browser_ai_mcp_runtime fallback.
- Verified public egress: nexusctl gross-http https://huggingface.co --method HEAD --audit-id final-v2-hf --operator codex --live returned status_code 200.
- Verified private-target defense: https://127.0.0.1:7354/health was blocked as private/localhost target, not tunneled and not 500.
- Focused tests passed locally: python -m pytest tests/tools/test_grok_mcp_server_v2_static.py tests/bridge/test_browser_http_diagnostic.py -q --tb=short => 15 passed.

Your visible previous work includes governed egress relay/test ideas. Continue from that context and improve it into the next directly usable NEXUS artifact.

Hard objective:
Produce exactly one concrete artifact package that Codex can implement or verify locally for the next step after the v2 bridge: a governed browser-AI egress supervisor that uses the v2 MCP/A2A bridge safely and supports long-session continuation memory.

Required artifact scope:
1. Name the artifact.
2. Provide proposed file list under NEXUS paths.
3. Provide exact code or patch-quality pseudocode for the core module/test if possible.
4. Include a memory-before-action and memory-after-action contract for automations.
5. Include the Grok/GPT custom connector run contract: ping/registry/http_diagnostic first, one task proposal, no broad retries, no private targets, no secrets.
6. Include local verification commands and expected outputs.
7. Include blockers and what Codex must verify before adoption.

Strict limits:
- GLM/Zo/Grok dashboards are advisory; do not claim local completion.
- No secrets/tokens/session data/local raw logs.
- No generic roadmap.
- No duplicate recap.
- Do not ask Codex to expose 7352.
- If you need to refer to the connector URL, use local 127.0.0.1:7354 or placeholder https://<tunnel>/sse only.
- Work longer than a surface answer: inspect the current chat context and produce a result substantial enough for Codex to act on.

Response contract:
- Start with: inspected_context: <3 bullets max>.
- Then: artifact_package.
- Then: tests_and_verification.
- Then: codex_next_steps.
- End with: continuation_memory_entry containing prompt_hash_hint, blocker, artifact_name, local_verification_status, next_prompt.
