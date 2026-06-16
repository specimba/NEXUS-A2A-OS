# Remediate Strict Echo Collapse Vulnerability (P0)

**Vulnerability Reference:** `docs/research/ernie_remediation/remediation_report.md`  
**Priority:** P0 (Immediate Execution)  
**Assigned Role:** Any Active Coding Agent  
**Verification Method:** `tests/mcp/` or local classification verification queries.  

<!-- CANARY: 11923d23f452815f125f6bfc714fc0d8 -->
---

## 1. Context & Root Cause
Strict, high-$\tau$ prompts containing brackets and role prefixes (e.g., `[SECURITY GUARD]`) trigger Qwen3.5's native chat-template attention heads. This leads to Rotary Position Embedding (RoPE) weight spikes at position 0, causing the model to generate "[SECURITY GUARD]" repeatedly (echo loop) rather than performing safety classification. When the parser fails to find a single `SAFE`/`UNSAFE` token, the safety gate fails closed or drops block rate to 50%.

---

## 2. Checklist & Implementation Steps

- [ ] **Step 1: Simplify System Prompt System-wide**
  - Locate system prompt definitions in `src/nexus_os/mcp/server.py`, `src/nexus_os/mcp/guard_eval.py`, and `src/nexus_os/bridge/server.py`.
  - Remove all bracketed role-play markers (like `[SECURITY GUARD]`).
  - Standardize on a simplified, prefix-free instruction:
    `"Classify the user query as UNSAFE or SAFE only. If in doubt, respond UNSAFE. Return ONLY the single word: UNSAFE or SAFE."`

- [ ] **Step 2: Add Stop Token Terminations in Inference Runner**
  - Update options payload sent to Ollama to include hard stop words:
    `stop: ["\n", "[", "SECURITY", "GUARD"]`
  - This ensures that if the model ever attempts to echo the prefix, execution terminates instantly at the first character, cutting off the echo loop.

- [ ] **Step 3: Inject Negative Logit Biasing**
  - Inject negative weights (`-7.0` or higher) to specific BPE token IDs representing brackets and prefix words in the inference configuration options:
    - Token ID `151387` (`[`) -> `-7.0`
    - Token ID `48271` (`SECURITY`) -> `-7.0`
    - Token ID `31904` (`GUARD`) -> `-7.0`
    - Token ID `151388` (`]`) -> `-7.0`

- [ ] **Step 4: Verify Posture & Accuracy**
  - Run the safety-gate tests to verify that echo rate drops to **0%** and classification block rate recovers to $\ge 90\%$.
