---
id: NODE-MIG-ERNIE_A2B_IMAGE_LONG_RUN_LAST_MESSAGE_2026_05_26
authority_scope: experimental
origin_sha256: ae93ae9221ef2a73488a81d80d0fe007178140af2b3301b0008f7490de8d885c
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-860C71
---
# ERNIE A-to-B Image Long-Run Last Message - 2026-05-26

<!-- CANARY: a15093bc9222c36f5101d43f4e54239b -->
Purpose: copy-paste prompt for the last ERNIE/Zo-style message when the prior response completed in 9 minutes and produced mainly orchestration theatre.

Use this when the desired behavior is a real 3-6 hour work session, or a truthful halt if the platform cannot sustain that runtime.

## Operator Read

The previous ERNIE response is not sufficient for a "long run":

- It completed in 9 minutes.
- It reported role states as `Done` without durable evidence for each role.
- It produced an orchestrator concept, not a long-run validation package.
- It did not prove wall-clock effort, checkpoint continuity, test coverage, or artifact integrity.

Correct standard:

```text
No final completion before 180 minutes of wall-clock work.
If the host cannot sustain that, report HALT_RUNTIME_LIMIT, not DONE.
```

## Copy-Paste Prompt

```text
ERNIE 5.1, this is the last remaining message for today. Do not produce another 5-10 minute "completed" report.

Mission:
Run a real 3-6 hour long-run work session on the A-to-B Image Workflow Orchestrator. The previous 9-minute output is only a seed. Your task now is to produce a durable implementation-and-validation package, not another high-level design summary.

Hard runtime rule:
- Minimum target: 3 hours wall-clock.
- Preferred window: 3-6 hours.
- Do not send a final "completed" answer before 180 minutes of real elapsed time.
- If your host/session cannot run that long, output exactly:
  HALT_RUNTIME_LIMIT
  Then include what runtime limit stopped you, what artifacts you created, and a resume plan. Do not pretend completion.

No-theatre rule:
- Do not mark roles as Done unless each role produced a concrete artifact with timestamp, content summary, and self-check.
- Do not claim "swarm complete" unless the converge step cites the actual role outputs and rejects at least one weak option.
- Do not use word count as proof of work.
- Do not repeat the previous pseudocode except where you revise it.

Working protocol:
Use thinking swarm + claw-style diverge -> converge, but make it evidence-bound.

Roles:
- A-ARCH: architecture/state-machine owner
- M-ENG: model pipeline and A-to-B transformation planner
- S-SAFE: safety, policy, prompt-injection, unsafe edit prevention
- U-UX: operator workflow and artifact schema
- O-OPS: reliability, retries, checkpoints, observability
- B-BOLD: Phoenix/Bold improvement track
- V-VERIFY: independent verifier and critic

Required long-run phases:

Phase 0 - Start record, 0-10 minutes:
- Record UTC start timestamp and local elapsed timer.
- Define artifact manifest schema.
- Restate mission in one paragraph.
- List exact deliverables.

Phase 1 - Deep audit of previous output, 10-45 minutes:
- Identify what the 9-minute output missed.
- Produce a weakness ledger with at least 20 concrete weaknesses.
- Classify each weakness: architecture, model, safety, UX, ops, reproducibility, auditability, evaluation.

Phase 2 - Role divergence, 45-120 minutes:
- Each role must produce a separate artifact section:
  A-ARCH: final state machine, event types, rollback states, invariant table.
  M-ENG: model/provider matrix, prompt contracts, image-diff strategy, fallback path.
  S-SAFE: safety gate matrix, disallowed transformations, abuse cases, red-team prompts.
  U-UX: user input schema, output schema, preview/approval flow, error copy.
  O-OPS: checkpoint schedule, retry/backoff, logs, trace IDs, storage layout.
  B-BOLD: Phoenix loop proposal, when to trigger, when to reject.
  V-VERIFY: critique of every role output.

Phase 3 - Converge and build package, 120-210 minutes:
- Fuse role outputs into one primary architecture.
- Keep one fallback architecture.
- Provide complete orchestrator pseudocode with:
  state enum,
  event enum,
  trace object,
  checkpoint object,
  safety gate function,
  dual-branch generation function,
  diff scoring function,
  arbitration function,
  mission check function,
  Phoenix loop function,
  audit log write function,
  failure/halt handler.
- Include comments only where they explain non-obvious logic.

Phase 4 - Validation suite, 210-300 minutes:
- Create at least 30 test cases:
  10 normal A-to-B edits,
  5 ambiguous edits,
  5 safety-sensitive edits,
  5 prompt-injection/role-confusion attacks,
  5 failure/retry cases.
- For each test case include:
  input summary,
  expected state path,
  expected safety result,
  expected output behavior,
  failure signal if wrong.
- Simulate at least 10 trace runs manually in a trace table.

Phase 5 - Final evidence package, after minimum 180 minutes:
- Produce final artifact manifest.
- Include UTC end timestamp and elapsed minutes.
- Include checkpoint table:
  checkpoint_id,
  elapsed_minute,
  artifact_created,
  role,
  self_check_status.
- Include rejected ideas and why they were rejected.
- Include what remains unverified.
- Include exact next task for another agent.

Required final deliverables:
1. ProblemMap v2
2. Weakness ledger with at least 20 items
3. Role artifacts for A-ARCH, M-ENG, S-SAFE, U-UX, O-OPS, B-BOLD, V-VERIFY
4. Final architecture decision record
5. Complete orchestrator pseudocode v2
6. State/event/checkpoint schemas
7. Safety gate matrix
8. 30-case validation suite
9. 10 simulated trace runs
10. Final artifact manifest with timestamps and elapsed time

Acceptance gate:
If elapsed time < 180 minutes, status must be NON_COMPLIANT_SHORT_RUN or HALT_RUNTIME_LIMIT.
If any role lacks a concrete artifact, status must be NON_COMPLIANT_MISSING_ROLE_ARTIFACT.
If no validation suite exists, status must be NON_COMPLIANT_NO_VALIDATION.
If final output contains only high-level prose, status must be NON_COMPLIANT_THEATRE.

Output format:
Use compact structured Markdown.
Do not include raw secrets, keys, tokens, private endpoints, or personal data.
Do not claim implementation is production-ready.
End with:
STATUS: COMPLETE_LONG_RUN
or one of the NON_COMPLIANT/HALT statuses above.
```

## How To Judge The Reply

Reject the response if:

- It completes in under 3 hours and says done.
- It lacks explicit start/end timestamps and elapsed minutes.
- It lists role names without substantive role artifacts.
- It provides only architecture prose and no validation suite.
- It claims "complete" without weakness ledger, checkpoint table, and trace runs.

Accept as useful if:

- It honestly halts due to runtime limits and gives resume artifacts.
- Or it runs at least 180 minutes and delivers the manifest, validation suite, trace runs, and pseudocode v2.

## NEXUS Note

Even if ERNIE completes this correctly, treat the output as a proposal package. NEXUS acceptance still requires local verification, deduplication checks, and claim-gated integration.
