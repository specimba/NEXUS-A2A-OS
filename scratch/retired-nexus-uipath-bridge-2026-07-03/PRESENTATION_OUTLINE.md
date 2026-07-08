# Slide Deck Outline: NEXUS-Maestro Case Integration

Use this slide deck structure to prepare your hackathon presentation.

---

## Slide 1: Title Slide
*   **Slide Title:** NEXUS-Maestro: Governed Enterprise Agentic Case Management
*   **Subtitle:** Building Safe, Auditable, and Cost-Effective Agentic Workflows
*   **Visual:** Architecture overview icon showing UiPath Cloud linked to NEXUS OS.
*   **Presenter Notes:** Introduce the team and state the core focus: bridging the gap between local AI prototypes and production-grade governed automations.

---

## Slide 2: The Enterprise Agentic Gap
*   **Slide Title:** Why AI Agents Fail in Production
*   **Key Points:**
    *   *Security Risks:* Direct database access leaves systems vulnerable to indirect prompt injections (CSI/ALSB) hidden in user inputs.
    *   *Lack of Control:* Purely autonomous LLM chains make decisions in black-box environments with no human-override gates.
    *   *Auditability Gaps:* Regulated enterprises require strict compliance trails for every model decision.
*   **Visual:** A warning icon next to a list of vulnerabilities.

---

## Slide 3: The Architecture Split
*   **Slide Title:** Control Plane vs. Reasoning Plane
*   **Key Points:**
    *   **Control & Execution Plane (UiPath Automation Cloud):** Orchestrates cases, triggers RPA robots, configures SLAs, and manages Human-in-the-Loop tasks via Action Center.
    *   **Reasoning & Governance Plane (NEXUS OS):** Sanitized policy adapter evaluating release safety, model hash validation, and outputting tamper-proof audit fingerprints.
*   **Visual:** Mermaid diagram showing the flow between UiPath Cloud and the Policy Adapter.

---

## Slide 4: Sentinel Case Workflow (Track 1)
*   **Slide Title:** Governed AI-Release Recovery Flow
*   **Key Points:**
    *   *Intake & Triage:* Robot ingests the release request; adapter identifies mismatched model hashes and issues a `HOLD` verdict.
    *   *Human-in-the-Loop:* Action Center routes a task to the AI Release Manager to confirm the remediation.
    *   *Remediation & Loop Recovery:* Robot executes safe rollback. If post-deployment verification fails, the case loops back to Investigation rather than failing silently.
*   **Visual:** Screen capture of the Maestro Case stage view.

---

## Slide 5: The Coding Agent Synergy
*   **Slide Title:** Built with UiPath for Coding Agents
*   **Key Points:**
    *   Development speed boosted by combining low-code components with specialized coding agents (Codex, Cursor, Gemini CLI).
    *   Coding agents read codebase schemas to generate contract tests, build JSON-RPC payloads, and scaffold the Fast API service.
    *   Command line validation verified with the `@uipath/cli` (`uip`) tool.
*   **Visual:** Command line terminal showing clean unit test compilation (`14 passed`).

---

## Slide 6: Business ROI & Production Feasibility
*   **Slide Title:** Value Delivered to the Enterprise
*   **Key Points:**
    *   *0% Execution Exposure:* Risk is neutralized at the policy gate before any agent triggers.
    *   *Auditability:* Every transition generates a secure hash record (`audit_id`) for retrospective compliance.
    *   *Enterprise Feasibility:* Fully decoupled from GPU requirements, allowing immediate, lightweight deployment to standard container services (Docker).
*   **Presenter Notes:** Summarize the submission and wrap up for Q&A.
