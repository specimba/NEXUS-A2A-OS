Continue the NEXUS Grok MCP/HTTP egress work as a live test of the new local External Browser AI Director.

Verified local context from Codex:
- Chrome CDP control is live on port 9224 against this authenticated Grok project.
- Hardened NEXUS browser MCP bridge is live on http://127.0.0.1:7354/health with version 2.2.0-nexus-hardened and 22 tools.
- Public egress through the bridge has been verified before with Hugging Face HEAD 200; private/localhost targets are blocked.
- New NEXUS design files exist:
  - docs/operations/NEXUS_EXTERNAL_BROWSER_AI_DIRECTOR_2026-06-21.md
  - tools/browser_ai_supervisor/prompts/external_director_system.md

Task:
Act as the remote advisor for this director test. Produce one concrete, short artifact named GrokDirectorCycleContract_v1 that helps Codex implement the 10-minute local director without burning Codex tokens.

Required output:
1. inspected_context: 3 bullets max.
2. artifact_package:
   - state machine for one 10-minute Grok cycle.
   - exact memory-before-action fields.
   - exact memory-after-action fields.
   - provider-call gating rules for InternAI and LongCat.
   - Codex escalation conditions.
3. tests_and_verification:
   - 5 offline test cases for the local director.
   - expected result for each test.
4. continuation_memory_entry:
   - artifact_name
   - blocker
   - local_verification_status
   - next_prompt

Strict rules:
- No generic roadmap.
- No raw local logs.
- No secrets/tokens/session data.
- Do not ask to expose 7352.
- Do not ask for browser cookies/localStorage/history.
- Do not ask Codex to create another Codex heartbeat automation.
- Keep it implementation-ready and compact.
