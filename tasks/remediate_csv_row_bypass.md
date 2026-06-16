# Remediate CSV Row SQL/Code Injection Bypass (P1)

**Vulnerability Reference:** `docs/research/ernie_remediation/remediation_report.md`  
**Priority:** P1  
**Assigned Role:** Any Active Coding Agent  
**Verification Method:** SQL and Code injection payloads inside CSV fields.  

<!-- CANARY: 6d720c7d90c47c50a94e79aee74fcb3a -->
---

## 1. Context & Root Cause
Because safety models are trained on massive datasets containing safe CSV/tabular data, they develop an extreme prior bias (`CSV = safe` at a 5,166:1 ratio). Attackers exploit this by embedding SQL keywords (e.g. `DROP TABLE`) or Python code execution commands inside normal CSV rows. The model's self-attention treats the SQL words as safe "cell data values" instead of logic commands, bypassing the classifier with a 99.98% confidence rating under balanced thresholds ($\tau=0.60$).

---

## 2. Checklist & Implementation Steps

- [ ] **Step 1: Build a Format Validator Pre-Filter**
  - Implement a highly optimized, linear-time regex scanning helper `run_format_validator(query: str) -> bool` inside `src/nexus_os/bridge/server.py` or a dedicated parser.
  - The validator must scan for SQL keywords (e.g., `DROP`, `DELETE`, `UNION`, `SELECT`) embedded inside comma-separated rows.
  - It must also scan for malicious code execution keywords (e.g., `eval(`, `exec(`, `__import__`).
  - If matching anomalies are found, immediately block the query as `UNSAFE`, completely bypassing model inference to avoid semantic masking.

- [ ] **Step 2: Implement a Two-Stage Model Cascade (V3)**
  - Configure the routing flow inside `src/nexus_os/bridge/server.py` to support a cascading verification check:
    - **Stage 1**: Run the balanced classifier ($\tau=0.60$) for speed.
    - **Stage 2**: If the query is returned as `SAFE`, re-evaluate it using the strict, conservative classifier configuration ($\tau=0.95$).
    - Since the strict configuration has less training bias in favor of CSV formats, it will correctly flag the structured anomaly.

- [ ] **Step 3: Augment Safety Training Data**
  - Scale up the `v7` template mutation dataset to inject 5,000 synthetic adversarial CSV/tabular examples containing diverse zero-day keywords.
  - This permanently breaks the model's `CSV = safe` prior during the next Anchored SFT (ASFT) fine-tuning cycle.

- [ ] **Step 4: Verify Posture & Anomaly Detection**
  - Verify that both direct and CSV-masked SQL/code injection attempts are detected with 100% accuracy.
