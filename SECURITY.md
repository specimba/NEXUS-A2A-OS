# 🛡️ Security Policy: NEXUS OS & Doppleground Collective

This Security Policy outlines the security measures, supported versions, and vulnerability reporting procedures for **NEXUS OS** and the broader **Doppleground Foundation** open-source ecosystem.

---

## 🧬 Core Security Philosophy

NEXUS OS is a local-first, zero-trust orchestrator engineered to operate securely on local consumer hardware. Our security architecture adheres to the following paradigms:

1. **Immutable Cryptographic Provenance**: Every system action, configuration update, and execution result is verified through Verifiable Action Provenance (VAP) audit ledger chains.
2. **Post-Quantum Immunity (ASRCP-Q2)**: Migrated core TrustKernel signatures to **ML-DSA-65** lattice signatures and local Vault backups to **ML-KEM-1024** encryption to defend against future quantum factorization vectors.
3. **Zero Environment Leakage**: Storing raw credentials or API keys inside databases or repository files is strictly forbidden. Credentials must utilize environment parameters only.
4. **Execution Gating**: Mandatory KAIJU 4-variable access gates and TrustEngine v2.2 dynamic score logic actively evaluate trust states before executing side-effectful tools.

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
* 📧 **Email**: [security@doppleground.org](mailto:security@doppleground.org)
* 🔑 **PGP Encryption**: For highly sensitive reports, please encrypt your payload using the Doppleground Foundation Security Public Key (available upon request or via our key registries).

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
