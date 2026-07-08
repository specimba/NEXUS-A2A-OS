# NEXUS Sentinel Case

A governed AI-release incident recovery workflow for **UiPath AgentHack Track 1: Maestro Case**.

UiPath Automation Cloud is the control and execution plane. The NEXUS Sentinel Policy Adapter is a deterministic advisory service that evaluates release evidence, returns `ALLOW`, `HOLD`, or `DENY`, and emits an auditable case transition. It never performs remediation.

## Demonstrated Outcome

The reference case catches a model identity mismatch and incomplete evidence, holds privileged remediation for an AI Release Manager, verifies the remediation, reopens the case when the first verification fails, and closes only after every check passes.

## Architecture

```mermaid
flowchart LR
    I["Robot or API Intake"] --> M["UiPath Maestro Case"]
    M --> A["Agent Builder Triage"]
    A --> P["NEXUS Policy Adapter"]
    P -->|"HOLD or DENY"| H["Action Center Human Decision"]
    P -->|"ALLOW"| R["Bounded Remediation Task"]
    H -->|"Approved"| R
    R --> V["Verification Task"]
    V -->|"Failed"| X["Rework Required"]
    X --> M
    V -->|"Passed"| C["Closure"]
    P --> L["Audit Record"]
    V --> L
```

## UiPath Components

- Maestro Case and Case App own stages, transitions, SLAs, and case history.
- Agent Builder produces a structured triage summary; it does not authorize remediation.
- API Workflow invokes the policy adapter.
- Action Center records the accountable human decision.
- Robot/API tasks simulate bounded remediation and verification.
- UiPath for Coding Agents is used to validate the adapter contract and deployment package.

## Public API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Dependency-free liveness contract |
| `POST` | `/api/v1/case/evaluate` | Evidence and policy evaluation |
| `POST` | `/api/v1/case/verify` | Post-remediation verification |
| `GET` | `/api/v1/audit/{audit_id}` | Sanitized audit outcome retrieval |

The adapter rejects unknown fields and retains only a SHA-256 input fingerprint plus the structured outcome. Replaying an identical `request_id` returns the original result; changing its payload returns HTTP `409`.

## Run Locally

```bash
python -m pip install -r nexus_uipath_bridge/requirements.txt
uvicorn nexus_uipath_bridge.app:app --host 127.0.0.1 --port 8080
python -m pytest tests/bridge/test_uipath_sentinel_contract.py -q
```

Port `8080` is the standalone demo default. Port `7352` remains reserved for the private NEXUS Brain API and is not used by this service.

## Container

```bash
docker build -f nexus_uipath_bridge/Dockerfile -t nexus-sentinel .
docker run --rm -p 8080:8080 nexus-sentinel
```

Deploy the container to a public HTTPS service, then configure `SENTINEL_BASE_URL` in the UiPath API Workflow. No NEXUS private service, model, database, or credential is required.

## Demo Assets

- `samples/01-safety-hold.json`: mismatch plus missing evidence.
- `samples/02-approved-remediation.json`: corrected identity and approved action.
- `samples/03-verification-failed.json`: first verification forces re-entry.
- `samples/04-verification-passed.json`: final closure gate.
- `UIPATH_BUILD_GUIDE.md`: exact Maestro fields, stages, and transitions.
- `DEMO_SCRIPT.md`: resettable five-minute presentation sequence.
- `SUBMISSION.md`: Devpost-ready copy.
- `PRESENTATION_OUTLINE.md`: slide-by-slide deck content.

## Safety Boundaries

- No local paths, secrets, prompts, model weights, or private NEXUS evidence are included.
- The adapter does not call Ollama, Brain API, GMR, or a GPU guard model.
- `selected_model` reports the observed and policy-accepted release model; it does not claim inference occurred.
- Policy outcomes are advisory. UiPath remains the authoritative orchestrator.
- Numerical security, savings, and automation-rate claims are intentionally omitted unless reproduced.

## License

MIT. See `LICENSE`.
