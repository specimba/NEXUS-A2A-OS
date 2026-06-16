# NEXUS OS Security Enhancement Plan
## Based on SecurityBASEandCRYPTknowledge.txt Research
## Version: 2026-06-09
## Status: Proposal — Pending SPECI Approval

---

## Research Summary

The security research file (`SecurityBASEandCRYPTknowledge.txt`) contains 323 lines of curated security resources, including:
- **Vulnerability databases**: Cisco Talos (2,187 reports), CERT VU# notices, NVD/CVE
- **Malware/spyware**: Pegasus (most dangerous active), Stuxnet, Mirai, Duqu, Flame, Shamoon
- **Cryptography libraries**: Libgcrypt (marked "best"), Bouncy Castle, wolfSSL, Botan, Crypto++
- **Hash functions**: SHA-1/SHA-256, Whirlpool, Tiger, Skein, SHA-3
- **Ciphers**: AES, Serpent, Twofish, Threefish, Blowfish
- **Post-quantum cryptography**: Future-proofing against quantum attacks
- **MITRE ATT&CK**: TTP framework for threat modeling
- **Linux kernel vulns**: Dirty Frag (VU#980487), Copy Fail (CVE-2026-31431), SGLang RCE
- **Supply chain**: XZ Utils attack (2024), EvidenceForge

---

## Current Issues

### 1. File Hashing Too Slow (CRITICAL)
**Problem**: `archivist.py` uses SHA-256 for 59,790 files = ~3+ hours per scan  
**Impact**: Archivist unusable for real-time operations  
**Evidence**: `sha256sum` on 50k+ files in a 7.5GB ARCHIVIST takes 10+ seconds per batch

**Solution**: Use `blake3` or `xxhash` for non-cryptographic file fingerprinting
- **blake3**: 10x faster than SHA-256, still cryptographically secure
- **xxhash**: 50x faster, non-cryptographic but collision-resistant for file deduplication
- Keep **SHA-256** for cryptographic integrity checks (secrets, vault)

```python
# Fast fingerprinting (non-cryptographic)
import blake3  # pip install blake3
# or
import xxhash  # pip install xxhash

hash = blake3.blake3(data).hexdigest()  # ~10x faster than SHA-256
# or for file dedup:
hash = xxhash.xxh3_64(data).hexdigest()  # ~50x faster, 64-bit
```

### 2. Vault Encryption Missing (CRITICAL)
**Problem**: `vault/secrets/` contains sshkey.pem, env.txt, zilliz credentials — **unencrypted**  
**Risk**: Any agent with filesystem access can read all secrets  
**Solution**: Encrypt vault with AES-256-GCM via **Libgcrypt** (user's preferred library)

```python
# Python wrapper for libgcrypt via ctypes or PyCryptodome
from cryptography.fernet import Fernet  # Or better: AES-256-GCM
import os

# Generate master key from environment or prompt
MASTER_KEY = os.environ.get("NEXUS_VAULT_KEY")  # 32-byte key

# Encrypt file
aesgcm = AESGCM(MASTER_KEY)
nonce = os.urandom(12)
ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
```

### 3. No Malware Scanning (HIGH)
**Problem**: ARCHIVIST contains 1,590 files from untrusted sources, no scanning  
**Risk**: Pegasus-like spyware, infected models (Py.Malware.CodeExec detected in HuggingFace)  
**Solution**: Integrate **ClamAV** for file scanning
- Lightweight, open-source, command-line interface
- Can scan pickles, models, executables
- EvidenceForge for evidence chain validation

```python
import clamd  # pip install pyclamav

cd = clamd.ClamdUnixSocket()
result = cd.scan("/path/to/file")
```

### 4. Threat Model Not Documented (MEDIUM)
**Problem**: No MITRE ATT&CK coverage for NEXUS OS  
**Solution**: Create threat matrix aligned with ATT&CK framework
- **T1190**: Exploit Public-Facing App (dashboard API)
- **T1003**: Credential Dumping (vault access)
- **T1486**: Data Encrypted for Impact (ransomware)
- **T1041**: Exfiltration Over C2 Channel (model data theft)

---

## Proposed Implementation

### Phase 1: Fast File Hashing (P0 — Immediate)
- Replace SHA-256 with `blake3` in `archivist.py`
- Expected: 3 hours → 15 minutes for full scan
- Keep SHA-256 for `vault/secrets/` cryptographic checksums

### Phase 2: Vault Encryption (P0 — Immediate)
- Implement AES-256-GCM encryption for `vault/secrets/`
- Key management: Environment variable + optional hardware key (YubiKey)
- Transparent decryption for authorized agents (trust score > 50)

### Phase 3: Malware Scanning (P1 — Short-term)
- Install ClamAV locally (`freshclam` for daily updates)
- Scan all new ARCHIVIST files before ingestion
- Block infected files (quarantine)

### Phase 4: Threat Model Documentation (P2 — Medium-term)
- Create `nexus_os/security/THREAT_MODEL.md` with MITRE ATT&CK mapping
- Map each NEXUS component to relevant TTPs
- Define detection rules for each attack vector

### Phase 5: Post-Quantum Cryptography (P3 — Long-term)
- Evaluate CRYSTALS-Kyber (NIST standardized KEM)
- Evaluate CRYSTALS-Dilithium (digital signatures)
- Prepare for quantum computer threats (5-10 year horizon)

---

## Key Libraries (User Preference Order)

1. **Libgcrypt** (GNU, marked "best" by user) — AES, RSA, ECC, hash functions
2. **Bouncy Castle** — Java/.NET crypto, widely used, FIPS-compliant options
3. **wolfSSL/wolfCrypt** — Embedded/lightweight, FIPS 140-2 certified
4. **Botan** — Modern C++ crypto, post-quantum support
5. **PyCryptodome** — Python wrapper for most of the above

---

## Encrypted File Policy

**`29&(][11!34.txt` is an encrypted file (NOT garbage).**
- **DO NOT rename, move, or delete** without SPECI approval
- **DO NOT hash or scan** without decrypting first (may corrupt encryption)
- **Store in `vault/secrets/` with encryption wrapper**
- **Document in `vault/ENCRYPTED_FILES.md`** with owner, encryption method, access policy

**Current encrypted files in vault:**
| Filename | Owner | Encryption | Purpose | Access Policy |
|----------|-------|------------|---------|---------------|
| `29&(][11!34.txt` | SPECI | Unknown | TBD | SPECI only |
| `sshkey.pem` | SPECI | Plaintext | SSH access | Trust score > 50 |
| `env.txt` | SPECI | Plaintext | Environment vars | Trust score > 50 |
| `zilliz_api_key` | SPECI | Plaintext | Vector DB | Trust score > 50 |
| `zilliz_token` | SPECI | Plaintext | Vector DB | Trust score > 50 |
| `zilliz_uri` | SPECI | Plaintext | Vector DB | Trust score > 50 |
| `cloud_region` | SPECI | Plaintext | Cloud config | Trust score > 50 |
| `cloud_cluster_id` | SPECI | Plaintext | Cloud config | Trust score > 50 |

---

## Next Steps

1. **P0: Fix archivist hashing** — Replace SHA-256 with blake3 (15 min implementation)
2. **P0: Encrypt vault** — AES-256-GCM for all secrets (2 hours implementation)
3. **P1: Install ClamAV** — Scan ARCHIVIST files (30 min setup)
4. **P2: Threat model** — Document MITRE ATT&CK mapping (4 hours)
5. **P3: Post-quantum** — Evaluate CRYSTALS-Kyber (research phase)

---

*Security enhancement plan based on `SecurityBASEandCRYPTknowledge.txt` research.*
*Author: SPECI | Date: 2026-06-09*
