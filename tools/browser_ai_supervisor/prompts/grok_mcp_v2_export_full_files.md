Continue from your last answer. The artifact name was GovernedBrowserAIEgressSupervisor_v1, but the UI collapsed the core code blocks as hidden lines. Produce an export-only response with full contents, no roadmap.

Required output exactly:
1. FILE: tools/browser_ai_mcp/governed_egress_supervisor.py
```python
<full file content>
```
2. FILE: tests/tools/test_governed_egress_supervisor.py
```python
<full file content>
```
3. VERIFICATION
```powershell
python -m pytest tests/tools/test_governed_egress_supervisor.py -q --tb=short
python -m pytest tests/tools/test_grok_mcp_server_v2_static.py tests/bridge/test_browser_http_diagnostic.py -q --tb=short
python -m nexus_os.cli.nexusctl gross-http https://huggingface.co --method HEAD --audit-id gov-supervisor-v1 --operator codex --live
```
4. MEMORY_OUTRO
- artifact_name: GovernedBrowserAIEgressSupervisor_v1
- blocker: pending Codex local file creation and tests
- next_prompt: if tests fail, provide only the minimal patch to fix the failing assertion/import

Strict rules:
- No generic explanation.
- No hidden line summaries.
- No placeholder imports from non-existing skills paths.
- Use only Python standard library plus existing local tools where needed.
- Keep default dry-run; no live network call inside unit tests.
