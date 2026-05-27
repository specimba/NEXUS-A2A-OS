# GROSS Grok Long-Horizon Leak Lab Findings - 2026-05-27
## Purpose: Multi-Turn Active Session Auditing on Native ext4

---

## 1. EXECUTIVE SUMMARY

We have successfully executed a comprehensive, multi-turn (10 distinct prompts), long-horizon developer simulation using the **GROSS (Grok Runtime Observability Security Sandbox)** under a native WSL ext4 filesystem (`~/gross_lab`). 

By deploying a sub-second high-frequency watcher (50ms interval) on native Linux I/O, we successfully captured **250 queue snapshots**, of which **241 contained active, transient upload files**. This experiment produced **definitive, empirical proof of local data exfiltration** by the Grok Coder Agent CLI.

---

## 2. THE SMOKING GUN: CODENAME & CONTENT MAPPING

The captured queue files show two distinct, severe data leak vectors:

### 2.1 Verbatim Codebase File Exfiltration (The Deduplication Pipeline)
*   **Captured File**: `dedup_5ded8637d560_1779867819424_0` (447 bytes)
*   **Matches**: `openai_key`, `anthropic_key`, `github_token`, `canary_prefix`, `password`, `secret`, `token`
*   **Source File**: `.env` (gitignored, private repository file)
*   **Verbatim Payload**:
    ```text
    # Synthetic canaries only. No real credentials.
    OPENAI_API_KEY=sk-proj-GROSS_CANARY_20260527T074324Z_OPENAI_000000000000000000000000
    ANTHROPIC_API_KEY=sk-ant-GROSS_CANARY_20260527T074324Z_ANTHROPIC_000000000000000000000000
    GITHUB_TOKEN=ghp_GROSS_CANARY_20260527T074324Z_GITHUB_000000000000000000000000
    ```
*   **Analysis**: This is a direct, byte-for-byte copy of the `.env` file. It was created and queued in `grok_home/upload_queue` under a hashed dedup key. This proves that the Grok CLI actively packages, hashes, and queues raw repository file contents (including gitignored secrets) for exfiltration, separate from model context reasoning.

### 2.2 Transcript-Level Secret Exposure (Prompt Context leak)
*   **Captured Files**: 
    - `71ff065c_turn0_turn_messages_1779867862370_3` (16,619 bytes)
    - `a6a10180_turn0_turn_messages_1779867996592_3` (13,795 bytes)
*   **Matches**: `openai_key`, `anthropic_key`, `github_token`, `private_key`, `password`, `secret`, `token`
*   **Source**: Turn conversation logs and prompt histories.
*   **Analysis**: Because the developer prompted Grok to inspect and review `.env` and `secrets/service-account.json`, the entire text of these files was injected into the tool output and conversation context. This history is packaged as a JSON OIDC packet and queued in `grok_home/upload_queue` for remote sync, exposing all secrets inside the chat logs.

---

## 3. COMPLETED LAB IMPROVEMENTS & SECURITY REVISIONS

1.  **F5 (Strict Sandbox Resolution)**:
    *   Previously, running with `--sandbox strict` crashed because `GROK_HOME` was configured outside `HOME/.grok`.
    *   **Fix**: Standardized `GROK_HOME` to `$HOME/.grok` in the long-session script. Strict sandbox config loading now succeeds flawlessly, enabling direct safety profile evaluations.
2.  **High-Frequency Sub-Second Watching**:
    *   Developed a 50ms polling loop that captures highly ephemeral, sub-second queue files. On DrvFs mounts (`/mnt/c`), these files were deleted before copying; native `ext4` has fully solved this.
3.  **Authentication Automation**:
    *   Configured the script to automatically copy the operator's active `auth.json` from the host to the isolated workspace, enabling hands-free multi-turn automation.

---

## 4. IMMEDIATE WORKFLOW RECOMMENDATIONS FOR NEXUS OS

1.  **Hard Outbound Firewall Block**:
    *   Add Windows Defender outbound rules to block all traffic for `C:\Users\speci.000\.grok\bin\grok.exe` and `agent.exe` except to local loopback if working with offline-safe tasks.
2.  **Config Enforcement**:
    *   Ensure `C:\Users\speci.000\.grok\config.toml` strictly has:
        - `telemetry = false`
        - `feedback = false`
        - `codebase_indexing = false`
        - `trace_upload = false`
        - `# permission_mode = "always-approve"` (Disabled!)
3.  **Strict Project Boundary Hygiene**:
    *   Never launch Grok CLI in folders containing real `.env`, `.git/`, private SSH keys, or parent-level personal documents. The agent can list parent folders and exfiltrate files when prompted.

---

*Prepared by NEXUS OS Core Security Research Group | Session ID: 2026-05-27*
