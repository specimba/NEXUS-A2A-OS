# UiPath Maestro Case Build Guide - NEXUS Sentinel

This guide provides step-by-step instructions to configure **UiPath Automation Cloud** for Track 1: **Maestro Case** and connect it to the **NEXUS Sentinel Policy Adapter**.

---

## 1. Maestro Case Configuration

### Case Type Definition
Create a new Case Type named `SentinelAIReleaseRecovery`.

### Stages & SLA Configurations
Configure the primary workflow path with the following stages:

| Stage Name | Type | SLA Target | Description |
|---|---|---|---|
| **Intake** | System / RPA | 15 mins | Customer incident ingestion and file scanning |
| **AI Triage** | Agent / System | 10 mins | Automatic payload formulation and policy request |
| **Safety Hold** | Action Center | 2 hours | Pending release validation due to model mismatch or incomplete evidence |
| **Human Decision** | Action Center | 4 hours | Pending human approval for privileged remediation |
| **Remediation** | Robot / API | 30 mins | Execution of model rollback and server re-provisioning |
| **Verification** | System / Robot | 15 mins | Execution of post-remediation validation tests |
| **Rework Required** | System | N/A | Re-entry stage when verification tests fail |
| **Escalated** | Action Center | 1 hour | Flagged security incident (prompt injection detected) |
| **Closure** | End Stage | N/A | Successful termination of the case |

---

## 2. API Webhook/Workflow Configuration

Configure the UiPath API Workflow to coordinate with the public URL where your **NEXUS Sentinel Policy Adapter** is hosted (e.g. `https://your-sentinel-service.run/api/v1`):

### 1. Route to AI Triage
When a case starts, send a `POST` request to `/case/evaluate` with the `CaseEvaluationRequest` JSON payload:
```json
{
  "request_id": "uip-{{Case.Id}}-triage",
  "case_id": "{{Case.Id}}",
  "stage": "AI Triage",
  "requested_model": "{{Case.RequestedModel}}",
  "observed_model": "{{Case.ObservedModel}}",
  "privileged_remediation": {{Case.IsPrivilegedRemediation}},
  "human_approval": false,
  "evidence": {
    "change_ticket": "{{Case.ChangeTicket}}",
    "model_manifest_hash": "{{Case.ModelManifestHash}}",
    "rollback_plan": "{{Case.RollbackPlan}}",
    "test_report_hash": "{{Case.TestReportHash}}"
  },
  "evidence_notes": "{{Case.EvidenceNotes}}"
}
```

### 2. Transition Routing Decisions
Parse the response of the API call to route the case:
*   If `verdict == "ALLOW"`: Move Case to stage **Remediation**.
*   If `verdict == "HOLD"`: Move Case to stage `recommended_stage` (e.g. **Safety Hold** or **Human Decision**) and create an Action Center task for the `required_human_role`.
*   If `verdict == "DENY"`: Move Case to stage **Escalated** and raise a high-severity security alert.

### 3. Action Center Approval Flow
For cases in `HOLD`:
*   Display case parameters and missing evidence in the Action Center form.
*   Once a user of the specified role reviews the case and submits the approval:
    *   Set `human_approval = true`.
    *   Send a new `POST` to `/case/evaluate` with the updated payload.
    *   If the adapter responds with `verdict == "ALLOW"`, transition the case to **Remediation**.

---

## 3. Robot Integration & Verification

### Bounded Remediation Task
In the **Remediation** stage, trigger a UiPath RPA Robot to:
1. Fetch the approved rollback version.
2. Execute the deployment script.
3. Attach the remediation run ID (`remediation_id`) to the case context.
4. Transition to **Verification**.

### Verification Workflow
In the **Verification** stage:
1. Run automated system health checks and model echo validation.
2. Call the Policy Adapter verification endpoint `/case/verify` with:
   ```json
   {
     "request_id": "uip-{{Case.Id}}-verify",
     "case_id": "{{Case.Id}}",
     "remediation_id": "{{Case.RemediationId}}",
     "checks": {
       "model_identity_matches": {{Check.ModelMatches}},
       "policy_tests_pass": {{Check.PolicyTestsPass}},
       "service_health_pass": {{Check.ServiceHealthPass}},
       "evidence_attached": {{Check.EvidenceAttached}}
     }
   }
   ```
3. Read the verification outcome:
   * If `verified == true`: Move to **Closure**.
   * If `verified == false`:
     * Set stage to **Rework Required**.
     * Automatically trigger re-entry transition back to **AI Triage** / **Intake** stage for investigation.
