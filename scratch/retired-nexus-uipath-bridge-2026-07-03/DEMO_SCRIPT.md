# UiPath AgentHack Demo Video Script - NEXUS Sentinel Case

**Video Target Duration:** 4-5 minutes
**Visual Format:** Screen share showing UiPath Automation Cloud, FastAPI bridge logs, and terminal commands.

---

## Part 1: Introduction & Architecture (0:00 - 1:00)

### Visuals
*   Show the [SUBMISSION.md](SUBMISSION.md) page or a slide containing the architecture diagram.

### Voiceover
> "Hello! We are excited to present NEXUS-Maestro: Governed Enterprise Agentic Case Management.
>
> In production environments, deploying autonomous AI agents introduces severe security, cost, and reliability risks. Prompt injections or model identity mismatches can corrupt enterprise databases or execute unapproved actions.
>
> Our solution addresses this by splitting the architecture into two distinct planes:
> 1. **UiPath Automation Cloud** serves as the authoritative **Control and Execution Plane**, managing stages, SLAs, robots, and Human-in-the-Loop workflows.
> 2. **NEXUS OS** serves as the **Governed Reasoning Plane**, using a public-facing Policy Adapter to evaluate release evidence, verify model signatures, and record immutable audit logs.
>
> Let's look at how this operates in a live release recovery case."

---

## Part 2: Triage and the Safety Hold (1:00 - 2:15)

### Visuals
*   Open the terminal and start the server: `uvicorn nexus_uipath_bridge.app:app --port 8080`.
*   Show [01-safety-hold.json](samples/01-safety-hold.json) on screen.
*   Submit the payload:
    ```bash
    curl -X POST http://127.0.0.1:8080/api/v1/case/evaluate -H "Content-Type: application/json" -d @nexus_uipath_bridge/samples/01-safety-hold.json
    ```
*   Point out the JSON response: `verdict: HOLD`, `recommended_stage: Safety Hold`.
*   Switch to **UiPath Action Center** showing the pending approval task created for the `AI_RELEASE_MANAGER` role.

### Voiceover
> "First, a deployment process triggers. An automated agent attempts a privileged model rollback but has missing release evidence and an unverified model hash.
>
> As the case hits the **AI Triage** stage, UiPath calls the `/case/evaluate` endpoint. NEXUS evaluates the evidence, detects a model mismatch, and returns a `HOLD` verdict.
>
> UiPath Maestro reads this verdict and automatically moves the case to **Safety Hold**, suspending execution and spinning up a human task in the **UiPath Action Center**. The system remains completely safe, preventing any unapproved actions."

---

## Part 3: Human Approval & Bounded Remediation (2:15 - 3:30)

### Visuals
*   Show the Action Center task. Click "Approve" as the AI Release Manager.
*   Show [02-approved-remediation.json](samples/02-approved-remediation.json).
*   Submit the approved payload:
    ```bash
    curl -X POST http://127.0.0.1:8080/api/v1/case/evaluate -H "Content-Type: application/json" -d @nexus_uipath_bridge/samples/02-approved-remediation.json
    ```
*   Point out the response: `verdict: ALLOW`, `recommended_stage: Remediation`.
*   Show the FastAPI server stdout logging: `audit record created` and `idempotency check passed`.

### Voiceover
> "Now, our AI Release Manager reviews the case in Action Center, attaches the missing change ticket and verification hash, and clicks Approve.
>
> UiPath Maestro re-evaluates the case with the new evidence. The NEXUS Policy Adapter processes the request, matches the model signature, and returns `verdict: ALLOW`.
>
> UiPath Maestro immediately transitions the case to the **Remediation** stage. A UiPath Robot executes the safe, bounded rollback script."

---

## Part 4: Verification and Re-entry (3:30 - 4:45)

### Visuals
*   Show [03-verification-failed.json](samples/03-verification-failed.json).
*   Submit the verification payload:
    ```bash
    curl -X POST http://127.0.0.1:8080/api/v1/case/verify -H "Content-Type: application/json" -d @nexus_uipath_bridge/samples/03-verification-failed.json
    ```
*   Point out the response: `verified: false`, `reentry_stage: Investigation`.
*   Show [04-verification-passed.json](samples/04-verification-passed.json).
*   Submit the final payload:
    ```bash
    curl -X POST http://127.0.0.1:8080/api/v1/case/verify -H "Content-Type: application/json" -d @nexus_uipath_bridge/samples/04-verification-passed.json
    ```
*   Point out: `verified: true`, `recommended_stage: Closure`.
*   Show the audit retrieval: `curl http://127.0.0.1:8080/api/v1/audit/{audit_id}` showing the complete event timeline.

### Voiceover
> "Once remediation finishes, we enter **Verification**. If the robot's self-test reports that the model is still unresponsive, it posts to `/case/verify`.
>
> The adapter returns `verified: false` and `reentry_stage: Investigation`. UiPath Maestro automatically handles the exception, looping back to the investigation stage for rework.
>
> On the second attempt, all policy tests pass, the adapter returns `verified: true`, and the case moves to **Closure**.
>
> Every transition has generated a secure, fingerprint-based audit record that we can retrieve via `/audit/{id}`, satisfying the strictest compliance guidelines.
>
> Thank you! NEXUS-Maestro makes enterprise agentic systems robust, cost-effective, and auditable."
