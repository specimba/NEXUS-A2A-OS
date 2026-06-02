# 🛡️ Security Policy: NEXUS OS & Doppleground Collective

This Security Policy outlines the security measures, supported versions, and vulnerability reporting procedures for **NEXUS OS** and the broader **Doppleground Foundation** open-source ecosystem.

---

## 🧬 Core Security Philosophy

NEXUS OS is a local-first, zero-trust orchestrator engineered to operate securely on local consumer hardware. Our security architecture adheres to the following paradigms:

1. **Immutable Cryptographic Provenance**: Every system action, configuration update, and execution result is verified through Verifiable Action Provenance (VAP) audit ledger chains.
2. **Post-Quantum Immunity (ASRCP-Q2)**: Migrated core TrustKernel signatures to **ML-DSA-65** lattice signatures and local Vault backups to **ML-KEM-1024** encryption to defend against future quantum factorization vectors.
3. **Zero Environment Leakage**: Storing raw credentials or API keys inside databases or repository files is strictly forbidden. Credentials must utilize environment parameters only.
4. **Execution Gating**: Mandatory KAIJU 4-variable access gates and TrustEngine v2.2 dynamic score logic actively evaluate trust states before executing side-effectful tools.

> [!TIP]
> ### 💡 What is Post-Quantum Cryptography? (For Non-Technical Users)
> Standard encryption methods rely on math problems that today's computers find nearly impossible to solve. However, future **quantum computers** (extremely fast, powerful machines being built today) will easily crack these standard math problems.
>
> **Post-Quantum Cryptography** uses entirely new, complex mathematical structures (like lattices) that are specifically designed to remain uncrackable—even by the most advanced future quantum computers. Implementing this now ensures your private vaults remain secure long into the future (preventing "harvest now, decrypt later" attacks).

---

## 🛠️ Cryptographic Standards & Threat Modeling

NEXUS OS leverages the user-curated cutting-edge cryptographic selections and threat vectors documented in our canonical baseline:

### 1. Curated Cryptographic Library Integrations
*   **Libgcrypt Standard**: We model our low-level cryptographic functions, secure memory handles, and random number generation after the GNU **Libgcrypt** library (the absolute baseline standard for secure resource locking), combined with **Bouncy Castle** structures for post-quantum lattice representations.
*   **Multi-Cipher Agnostic Support**: In addition to standard **AES-256**, we integrate support for alternative high-security symmetric ciphers like **Serpent** and **Twofish** to provide robust cipher-diversification, securing our 5-track Vault storage tracks.
*   **Merkle–Damgård Integrity Hashing**: We secure system transaction sequences using double-hash chains and Whirlpool / SHA-256 one-way compression functions to guarantee immutable VAP provenance records.

### 2. Modern Exploit Mitigation (Threat Profile)
NEXUS OS is proactively hardened against major real-world vulnerabilities and attack methodologies:
*   **Local Privilege Escalation (e.g., Dirty Frag & Copy Fail)**: We mitigate page cache and memory manipulation attacks (such as the Linux kernel *Dirty Frag* and *Copy Fail* CVE-2026-31431 vectors where unprivileged users write controlled bytes to page cache) by enforcing strict process sandbox boundaries and PTY isolation.
*   **RCE in AI Runloads (e.g., SGLang Exploit Maps)**: We quarantine untrusted model weights and server wrappers (preventing remote code executions or directory traversals like SGLang's path traversal) by routing all model interactions through gated, authenticated wrappers on loopback ports.
*   **Zero-Click & PATN Countermeasures**: Inspired by NSO Group's *Pegasus* and *FORCEDENTRY* exploits (which use emulated JBIG2 computer architectures inside chat channels), all remote JSON-RPC payload structures are parsed via strict validation schemas, blocking nested executable instructions or dynamic clock-manipulation replay attacks.
*   **Bytecode & Malware Scanning (ClamAV & EvidenceForge)**: Before staging any agent tool or model bytecode, our ingestion bridge verifies the assets against automated static scan rules (modeled after Cisco Talos *EvidenceForge* and ClamAV signatures), immediately flagging any hazardous execution patterns like `Py.Malware.CodeExec___main___ANY_GLOBAL`.
*   **Kerberos-Compliant Clock Skew Rules**: To block packet capture, telnet spoofing, and ticket replay attacks, our bridge enforces a strict **300-second (5 minutes) maximum clock skew** rule across all agent authentication tokens.

---

## 📈 Supported Versions

We actively maintain and support versions that incorporate our post-quantum and local-first security infrastructure.

| Version Range | Supported | Description |
| :--- | :---: | :--- |
| **v7.x.x** | :white_check_mark: | Current Mainline (ASRCP-Q2 Immune, TrustEngine v2.2, FastAPI Governance REST Plane). |
| **v6.x.x** | :white_check_mark: | Previous Stable (Phase 0 Hardened, stdio MCP Server base). Security patches backported. |
| **v5.x.x and legacy** | :x: | Legacy releases. Legacy versions are deprecated; users are strongly encouraged to upgrade. |

---

## 🚨 Reporting a Vulnerability

We take the security of our decentralized, local-first ecosystem extremely seriously. If you discover a vulnerability or potential exploit, please follow our coordinated disclosure policy:

### 1. How to Report
Please do **not** open a public GitHub Issue for security bugs. Instead, submit reports through our secure private channel:
* 📧 **Email**: [specimba@gmail.com](mailto:specimba@gmail.com)
* 🔑 **PGP Encryption**: For highly sensitive reports, please encrypt your payload using our Security Public Key (available upon request or via our key registries).

### 2. What to Include in Your Report
To help us evaluate and patch the bug efficiently, please provide:
* A detailed description of the vulnerability and its potential impact.
* Clear steps to reproduce the issue (including proof-of-concept scripts or payload examples).
* Your details for proper attribution in our security ledger (you may remain anonymous if preferred).

### 3. Our Response Commitment
Upon receiving a report, the Doppleground Foundation security team will:
* Acknowledge receipt of the vulnerability within **24 hours**.
* Provide a status update and initial assessment within **72 hours**.
* Work collaboratively with you to validate the issue, prepare a patch, and coordinate a public release with proper credit.

---

## ⚖️ License & Attribution
Doppleground Foundation © 2026. Governed by the Commons. Distributed under the Apache 2.0 License.
