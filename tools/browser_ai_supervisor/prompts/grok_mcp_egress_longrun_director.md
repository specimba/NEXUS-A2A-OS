Continue the NEXUS MCP/HTTP sandbox egress work as a serious long-run implementation cycle.

You are in the NEXUS OS Grok project conversation. Use the last conversation context, attachments, code snippets, and your previous `mcp-egress-governor` attempt.

Current verified context from Codex:
- Direct Python HTTP from the sandbox failed with `<urlopen error [Errno 111] Connection refused>`.
- Existing discussion converged on MCP/HTTP egress delegation through proxy/bridge/tunnel/governor patterns.
- Your last artifact named `mcp-egress-governor` is useful as a direction but NOT acceptable as implementation evidence.
- Problems in the last artifact:
  - Python code is not syntactically safe as pasted: broken placeholder identifiers like `kai ju_gate`, indentation/rendering risk, undefined `check_token_guard`, placeholder imports.
  - It simulates proxy egress instead of implementing a verifiable proxy/bridge abstraction.
  - It claims a sha256/path from your sandbox, but Codex cannot trust it until you provide artifact content and verification instructions.
  - It does not map to actual NEXUS local modules or tell Codex what files to patch first.
  - It does not run a real 3-cycle verification loop or provide failure evidence.

Hard objective:
Produce a corrected, directly usable NEXUS implementation artifact package for a dry-run-first `mcp-egress-governor` / MCP egress bridge integration.

Required working style:
- Work for a real long cycle. Do not answer in a shallow 30-second summary.
- Inspect the current project/chat context before writing.
- If you have a sandbox terminal, create files and run syntax/tests there.
- Expand/check your own previous code blocks and fix defects before final answer.
- Do not execute destructive actions.
- Do not request secrets/tokens or expose browser/session data.
- Do not claim local NEXUS completion; Codex will verify locally.

Artifact requirements:
1. `SKILL.md` for `mcp-egress-governor`.
2. A valid Python module with no syntax errors:
   - safe dataclasses/types for `EgressRequest`, `EgressDecision`, `EgressResult`
   - `MCPEgressGovernor.assess_risk()`
   - `MCPEgressGovernor.plan_egress()` dry-run decision path
   - fail-closed allowlist behavior
   - no network call by default
   - optional proxy backend interface stub that is testable without live network
3. Integration patch proposal for actual NEXUS locations:
   - where to wire into `nexus_os/mcp/mcp_client.py` or equivalent
   - where to call TokenGuard/KAIJU/VAP if present
   - fallback behavior when those modules are absent
4. Tests:
   - syntax/import test
   - allowlisted read request returns dry-run proxy plan
   - non-allowlisted domain blocks
   - write/exec intent escalates to KAIJU-required or blocked
   - TokenGuard exhausted path blocks
   - no live network call in dry-run mode
5. Verification commands and expected outputs.
6. Changed-file list.
7. Blockers and local Codex verification instructions.
8. If files are generated in your sandbox, provide path, byte count, and sha256.

Response contract:
- First, state what you inspected from the last context.
- Then provide the corrected artifact package.
- Then provide tests/results.
- Then provide exact Codex next steps.
- No generic roadmap.
- No duplicate recap.
- No “ready” claim unless you show test evidence.

Target outcome:
Codex should be able to convert your output into a local NEXUS dry-run implementation and run tests without guessing your intent.
