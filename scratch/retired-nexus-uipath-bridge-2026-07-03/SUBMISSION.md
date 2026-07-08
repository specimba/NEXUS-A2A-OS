# Devpost Submission: NEXUS Sentinel Case

## Track

**Track 1: UiPath Maestro Case**

## Inspiration

Enterprise AI incidents rarely follow a clean linear process. A release can report the wrong model identity, arrive with incomplete evidence, require privileged remediation, fail verification, and return to investigation. Teams need automation, but they also need an accountable human to remain in control.

## What It Does

NEXUS Sentinel Case orchestrates AI-release incident recovery in UiPath Maestro. A case moves through Intake, AI Triage, Investigation, Human Decision, Remediation, Verification, and Closure. Dynamic secondary stages handle Evidence Missing, Safety Hold, Rework Required, and Escalated outcomes.

A lightweight NEXUS policy adapter evaluates model identity, evidence completeness, remediation privilege, approval state, and untrusted instruction indicators. It returns one of three deterministic verdicts:

- `ALLOW`: the case may advance to bounded remediation.
- `HOLD`: evidence or accountable approval is required.
- `DENY`: the case is escalated as a security incident.

Every result includes reason codes, the next recommended stage, the required human role, and an audit ID. Remediation cannot close the case. A separate verification task must pass every check; failure moves the case to Rework Required and re-enters Investigation.

## How We Built It

UiPath Automation Cloud is the authoritative control and execution plane:

- **Maestro Case** owns the lifecycle, dynamic stages, handoffs, and recovery loop.
- **Case App** provides the operator view and evidence checklist.
- **Agent Builder** creates structured triage observations.
- **API Workflow** calls the public NEXUS policy adapter.
- **Action Center** records high-risk approval decisions.
- **Robot/API tasks** perform bounded remediation and verification.
- **UiPath for Coding Agents** supports contract implementation and validation with Codex and Gemini.

The NEXUS adapter is deliberately independent from local models and private infrastructure. It exposes four strict FastAPI endpoints, stores no raw request content, and provides replay-safe idempotency. This makes the live workflow reliable while preserving a clear path to deeper NEXUS guard integrations after the hackathon.

## Demo Scenario

1. An AI release case requests `glm-5.2`, but runtime evidence reports a fallback model and omits required artifacts.
2. The adapter returns `HOLD`, `HIGH`, `MODEL_ECHO_MISMATCH`, and `EVIDENCE_INCOMPLETE`.
3. Maestro moves the case to Safety Hold and creates an Action Center task for an AI Release Manager.
4. The operator attaches evidence and approves a bounded remediation.
5. The first verification deliberately reports that model identity still mismatches.
6. Maestro moves the case to Rework Required and re-enters Investigation.
7. The corrected remediation passes all checks and the case closes with a complete audit trail.

## Challenges

The largest design challenge was avoiding orchestration theater. We rejected a design in which a local LLM service appeared to make settlement decisions. Instead, UiPath owns every transition and side effect while NEXUS supplies a narrow, testable policy contract. We also separated evaluation from verification so an approved action can still fail safely and re-enter the case lifecycle.

## Accomplishments

- Dynamic exception handling rather than a linear happy-path demo.
- Human approval bound to privileged remediation.
- Explicit failed-verification recovery and case re-entry.
- Strict `ALLOW/HOLD/DENY` API contract with stable reason codes.
- Idempotent requests and sanitized audit retrieval.
- No dependency on private NEXUS services, local GPUs, or model availability.

## What We Learned

Enterprise agent governance is strongest when policy advice, human accountability, execution, and verification are separate responsibilities. Maestro provides the durable control plane needed to keep those responsibilities synchronized as the case changes.

## What's Next

- Persist audit records in an enterprise datastore.
- Add signed webhook authentication and tenant isolation.
- Connect verified NEXUS GuardRouter evidence through an optional normalized adapter.
- Add Test Cloud regression packs for case transitions and third-party agent failures.
- Track operational measures such as time-to-triage, hold reasons, rework frequency, and mean time to verified recovery.

## Repository And License

The public repository contains the policy adapter, tests, sanitized samples, UiPath build guide, architecture, and demo materials. It is licensed under MIT. No private logs, credentials, model weights, or proprietary NEXUS research are included.
