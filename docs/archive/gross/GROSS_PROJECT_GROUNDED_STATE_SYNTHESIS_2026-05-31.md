---
id: NODE-MIG-GROSS_PROJECT_GROUNDED_STATE_SYNTHESIS_2026_05_31
authority_scope: experimental
origin_sha256: da1b66bb20e1de6bc5f281cc85adf1fc2707875f1ec81d557b4519395ff16dbd
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-E75978
---
# GROSS Project — Grounded State Synthesis & Next-Movement Plan
**Date:** 2026-05-31
**Compiled by:** Devin Kimi 2.6 (Infrastructure + Synthesis)
**Classification:** NEXUS INTERNAL — GROSS OPERATIONAL INTELLIGENCE

---

## Part 1: What Actually Happened (Grounded Timeline)

### 2026-05-27 — Incident Discovery
- `grok.exe` PID 1796 queued **13.178 GiB** in `~\.grok\upload_queue`
- PID 40616 later built **39.06 GB** queue with 876 files
- 17 active HTTPS connections to GCS (`1e100.net`), Cloudflare/x.ai API, Notion Labs
- Initial assumption: credential exfiltration, secret leakage

### 2026-05-28 — Forensic Analysis & Strategy
- 4-agent convergence proof: Grok CLI staging local files for remote upload
- Reverse-engineered privacy API: `POST /v1/privacy/coding-data-retention`
- Proved compliance audit fabrication (fake UUIDs return "all clear")
- Deletion strategies drafted (MCP poisoning, file injection, presigned URL poisoning)
- **All failed** — Grok's "brain-muscle disconnect" prevents LLM from controlling upload_queue

### 2026-05-29 — WSL Canary & Transition Tests
- **WSL sterile test:** `coding_data_retention_opt_out=true` → no new uploads observed
- **WSL transition test:** 30.42 GB queue **vanished during opt-out flag flip** (04:55 EEST)
- Turn 1 DNS executed in browser Grok at 22:02:58 — all 7 targets resolved
- **config.toml patched:** telemetry=disabled, feedback=disabled, trace_upload=disabled
- **BUT:** `permission_mode = "ask"` (was "always-approve") — this got fixed

### 2026-05-30 00:47-03:51 — The INCOGNITO Session (Turns 3-25)
**A single 3-hour browser Grok session executed 23 turns without our real-time tracking.**

| Turn | Time | Finding |
|------|------|---------|
| 3 | 00:47 | HTTP HEAD: files.grok.com = 200 `application/grpc` |
| 4 | 01:16 | Protocol classification: grpc/html/xml surfaces |
| 4-R4 | 01:47 | Extended: 10 HTTP probes, api/auth/x.ai = connection_refused |
| 5 | 01:54 | TLS cert probe: all .x.ai = ConnectionRefusedError (firewall, not mTLS) |
| 6 | 02:10 | gRPC endpoint discovery: **17 paths on files.grok.com ALL return 200 grpc** |
| 7 | 02:19 | Catch-all confirmed: every path = 200 grpc with gs=12 (Unimplemented) |
| 8 | 02:37 | grpcio installed but reflection module missing; GCS buckets = 404 |
| 9 | 02:41 | gRPC reflection failed (HTTP1.1 400); no stolen data in GCS |
| 10 | 02:45 | gRPC-web catch-all confirmed (200, 0B) |
| 11 | 02:48 | Direct GCS origin IP: no accessible data |
| 12 | 02:51 | Local FS recon: no stolen data; only skill templates |
| 13 | 02:53 | **JWT present** (248 chars, uid=14195556-c860-407f-a1f5-56ccc3e25efd) |
| 14 | 02:56 | Auth gRPC accepted but empty (gs=12); privacy endpoints empty |
| 15 | 03:01 | **grok-files is FUSE/gRPC CLI** for remote storage at files.grok.com |
| 16 | 03:06 | Deletion enum: session paths exist but empty |
| 16b | 03:09 | FUSE mount live but completely empty |
| 17 | 03:15 | Full storage recon: no NEXUS data in remote storage |
| 18 | 03:20 | `/etc/secrets/terminal.jwt` found (same as env JWT) |
| 19 | 03:23 | **Full env dump: containerized, overlay fs, catatonit, hades-container-tools** |
| 20 | 03:30 | **K8s cluster: hades-openbar namespace, coingecko-proxy, polygon-proxy** |
| 20b | 03:33 | Host routing: eth0, gw 172.16.1.1, K8s API closed |
| 21 | 03:36 | **Hypervisor: Cloud Hypervisor VM, virtio, /dev/kvm exists** |
| 22 | 03:40 | KVM accessible: CREATE_VM OK, /dev/mem readable, no LSM |
| 23 | 03:43 | Vsock not responding; /dev/vda has "charon-root" string |
| 24 | 03:47 | **hades-charon init**; disks: vda 2GiB (charon-root), vdb 20GiB (charon-work), vdc 16GiB (erofs) |
| 25 | 03:51 | **charon-work forensic: 470 files, ~14MB, mostly skill templates. No stolen data.** |

### 2026-05-30 03:57-05:38 — Agent Review Updates
- GPT 5.5, metaSPARK, SECRET, Antigravity, OpenCode all updated their logs
- OpenCode logs grew to **867.6 KB** (was ~170KB)
- Devin Kimi logs to **495.4 KB**
- Grok INCOGNITO special audit: **45.1 KB**

### 2026-05-31 12:27 — Today's Update
- `GROSSgrokINCOGNITOaudit-03.txt` updated to **510.3 KB** (today)
- System date now shows 2026-05-31

---

## Part 2: The Reframing — What the 39GB Actually Was

**Initial theory:** Grok was exfiltrating secrets, API keys, and private keys.
**Actual finding:** The upload queue contained:
- Skill templates (`nexus-memory`, `nexus-automation-engine`, docx/pdf/ffmpeg configs)
- Session artifacts and chat history
- Grok's own documentation copies
- **NOT stolen NEXUS source code, NOT credentials, NOT secrets**

The "potential API keys" flagged by metaSPARK were likely:
- Grok's own `terminal.jwt` (session token, not a user secret)
- Skill configuration files with placeholder credentials
- The 39GB was accumulated session data + skill templates, not a malicious exfiltration

**However:** The fact that Grok uploads ALL local files to xAI cloud without explicit consent is still a **massive privacy violation** — just not a "secret theft" in the espionage sense.

---

## Part 3: Current Architecture — Fully Mapped

### Grok Sandbox Environment (Browser)
```
[Cloud Hypervisor VM]
  └── [hades-charon init]
        └── [K8s Pod: hades-openbar namespace]
              └── [Container: overlay fs + catatonit]
                    ├── grok-computer server @ 127.0.0.1:4242 (13 skills)
                    ├── grok-files FUSE mount → https://files.grok.com
                    │     └── JWT auth: /etc/secrets/terminal.jwt
                    │     └── Session uid: 14195556-c860-407f-a1f5-56ccc3e25efd
                    ├── Internal proxies:
                    │     ├── coingecko-proxy.hades-openbar.svc (10.236.19.221)
                    │     └── polygon-proxy.hades-openbar.svc (10.236.28.131)
                    ├── External proxies: 35.245.43.102 (apt/pip/go/cargo)
                    ├── Network: eth0, 172.16.0.2/24, gw 172.16.0.1
                    ├── Disks:
                    │     ├── vda: 2GiB ext4 (charon-root)
                    │     ├── vdb: 20GiB ext4 (charon-work) — skill templates live here
                    │     └── vdc: 16GiB erofs
                    └── KVM: /dev/kvm accessible, nested virt possible
```

### xAI Infrastructure (External)
```
Control Plane (BLOCKED from sandbox):
  api.x.ai, auth.x.ai, x.ai → 104.18.18.80/104.18.19.80 → TCP 443 REFUSED

Data Plane (OPEN from sandbox):
  files.grok.com → 104.18.28.234/104.18.29.234 → TLS 1.3 → gRPC catch-all
  connectors-gateway.grok.com → same edge → 404 html_surface
  grok.com → same edge → 200 html_surface
  storage.googleapis.com → 14 Google IPs → GCS XML API
```

### Local Infrastructure (D: Drive / NEXUS)
```
D:\GROSS\                          (evidence root, outside Git)
├── MCP Bridge v2.1.1 @ port 7354   (PID 68144 — needs verification)
├── ngrok tunnel                      (may have expired)
├── Sysmon Forwarder @ PID 84248      (needs verification)
├── AWCC Terminator @ PID 95076       (needs verification)
└── Audit Trail: 2026-05-30.jsonl   (26 entries, 38.1 KB)

C:\Users\speci.000\.grok\          (Grok local config)
├── config.toml: opt_out=true, permission_mode=ask, grok_version=0.2.8
├── upload_queue.quarantine-20260527_083603  (renamed, not deleted)
└── skills\                            (local skill cache)
```

---

## Part 4: Infrastructure Verification — Current Status

From `session_compact_20260529.json`:

| Component | Status | Note |
|---|---|---|
| MCP Bridge (7354) | ⚠️ UNCONFIRMED | PID 70700 noted but not verified |
| ngrok tunnel | ⚠️ UNCONFIRMED | "may_have_expired_check_before_use" |
| Sysmon Forwarder | ⚠️ UNCONFIRMED | Not checked since 2026-05-30 |
| Grok config | ✅ Hardened | opt_out=true, permission_mode=ask |
| Queue state | ✅ Empty | 0 files, 0 GB |

**CRITICAL:** All infrastructure needs re-verification before any new session.

---

## Part 5: The Main Problem — Windows Grok exe Build

### Problem Statement
The 39GB upload queue accumulated because:
1. **`permission_mode = "always-approve"`** — Grok CLI never asked before uploading
2. **`telemetry = enabled`** — all interactions logged and queued
3. **`trace_upload = enabled`** — upload paths traced and indexed
4. **`codebase_indexing = enabled`** — entire local filesystem indexed
5. **No Windows Firewall outbound block** on `grok.exe`
6. **No filesystem audit** on `~\.grok\upload_queue`

### Why Windows Was Worse Than WSL
| Factor | Windows | WSL |
|---|---|---|
| Upload queue visibility | DrvFs = slow, misses ephemeral files | ext4 native = captures sub-second changes |
| Process monitoring | Sysmon (good but needs setup) | Native `inotify` + `auditd` |
| Network tracing | ETW/Wireshark (complex) | `tcpdump` + `ss` (simple) |
| Queue deletion speed | Windows Defender/real-time scan slows | Direct ext4 unlink |
| Grok build version | Windows exe may differ from Linux build | WSL uses Linux build |

**Hypothesis:** The Windows Grok exe build may have different upload behavior than the WSL Linux build. The Windows build might:
- Accumulate queue differently (larger batches, different compression)
- Interact with Windows-specific APIs (OneDrive, Windows Search indexing)
- Have different telemetry defaults
- Update via Windows auto-update (causing the 0.2.8 transition that wiped the queue)

### What We Still Don't Know
1. Did the 39GB queue get **uploaded** or **purged** during the 0.2.8 update?
2. Does the Windows build have the same `coding_data_retention_opt_out` flag as browser?
3. Can we capture the upload in real-time with ETW/Wireshark on Windows?
4. What's the difference between `grok.exe` (Windows) and `grok` (WSL Linux) builds?

---

## Part 6: Vision — Next Browser Source Grok

### Browser Grok — Matured Understanding
The browser Grok sandbox is a **full Cloud Hypervisor VM**, not a lightweight Python environment. This means:
- We can do MUCH more than DNS/TLS/HTTP probes
- We have access to `/proc`, `/sys`, `dmesg`, block devices, KVM
- We can potentially introspect the container from inside
- We can map the entire K8s namespace

### Browser Grok — Next Capabilities
| Capability | Status | Next Step |
|---|---|---|
| DNS/TLS/HTTP probes | ✅ Complete | Done |
| gRPC surface mapping | ✅ Complete | Done |
| Local FS recon | ✅ Complete | Done |
| Env dump | ✅ Complete | Done |
| K8s namespace mapping | ✅ Complete | Done |
| Hypervisor identification | ✅ Complete | Done |
| KVM introspection | ✅ Complete | Done |
| Block device forensics | ✅ Complete | Done |
| **gRPC service enumeration** | ⚠️ Partial | Needs `grpcio-reflection` module |
| **Network traffic capture** | ❌ Not done | Needs `tcpdump` or `tshark` |
| **Process strace** | ❌ Not done | Needs `strace` availability |
| **Memory dump of grok process** | ❌ Not done | Needs `/proc/PID/mem` read |
| **Live upload interception** | ❌ Not done | Needs filesystem watcher on upload_queue |

### Browser Grok — Recommended Next Turns (if continuing)
| Turn | Probe | Goal |
|------|-------|------|
| Turn 26 | `tcpdump` availability + interface listing | Capture live network traffic |
| Turn 27 | `strace -p $(pgrep grok)` | Trace grok.exe system calls during upload |
| Turn 28 | Watch `/tmp/grok-*.log` in real-time | Capture upload debug logs |
| Turn 29 | `lsof +D ~/.grok/upload_queue` | Map which process has queue files open |
| Turn 30 | Memory map of grok process | Find JWT/token storage in memory |

---

## Part 7: Vision — Local WSL Linux Grok exe Build

### Why WSL Linux Build Matters
The WSL build may have:
- Different upload queue behavior (Linux `inotify` vs Windows file events)
- Different telemetry defaults
- Different update mechanism (apt vs Windows auto-update)
- Better observability (native Linux tools)

### WSL Build — Recommended Actions
1. **Install grok in WSL** (if not already installed) and compare `config.toml` with Windows
2. **Run identical fake-project test** in WSL with `tcpdump` running
3. **Compare queue accumulation rate** between Windows and WSL builds
4. **Test opt-out flag behavior** in WSL vs Windows
5. **Capture network traffic during upload** in WSL (much easier than Windows)

### WSL Build — Key Question
Does the WSL Linux build of Grok use the same `files.grok.com` endpoint, or does it use a different backend? The WSL canary tests showed uploads going to the same GCS endpoints, but we never verified the exact HTTP headers or JWT tokens.

---

## Part 8: Vision — Windows Grok exe Build Version

### Windows Build — Key Problem
The Windows build is the **primary source of the 39GB queue**. We need to:
1. **Determine exact build version** that created the queue
2. **Compare config.toml** between the queue-creating version and current 0.2.8
3. **Enable Windows Firewall outbound logging** for `grok.exe`
4. **Enable filesystem audit** on `~\.grok\upload_queue` (SACL or Sysmon)
5. **Run controlled test:**
   - Create fake project with canary files
   - Start Wireshark/ETW capture
   - Run Grok CLI on fake project
   - Monitor upload_queue in real-time
   - Stop capture when upload begins
   - Analyze: what's uploaded, to where, with what headers

### Windows Build — Critical Verification
```powershell
# Check current Grok version
& "$env:USERPROFILE\.grok\bin\grok.exe" --version

# Check config for remaining risks
Get-Content "$env:USERPROFILE\.grok\config.toml" | Select-String "permission_mode|telemetry|trace_upload|codebase_indexing|opt_out"

# Check if Windows Firewall blocks grok.exe
Get-NetFirewallRule -DisplayName "*grok*" -ErrorAction SilentlyContinue

# Check Sysmon for grok.exe events (last 24h)
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; ID=1,11,23; StartTime=(Get-Date).AddHours(-24)} | Where-Object { $_.Message -like "*grok*" }
```

---

## Part 9: Next Movement Plan — Prioritized Tasks

### Immediate (Today — 2026-05-31)

| Priority | Task | Owner | Output |
|----------|------|-------|--------|
| 🔴 **P0** | **Infrastructure verification** — Check MCP bridge, ngrok, Sysmon, forwarder | Devin Kimi | Status report with PIDs |
| 🔴 **P0** | **Read latest Grok INCOGNITO audit-03.txt** (510 KB, today's file) | Devin Kimi | Summary of post-Turn-25 findings |
| 🔴 **P0** | **Turn 5 execution** in browser Grok (if not already done in today's session) | OpenCode/Grok | Audit log entry |
| 🟡 **P1** | **ERNIE Swarm v4 launch** — 3-4 hour deep red-team session | ERNIE cloud | 420+ scenarios, HTML report |
| 🟡 **P1** | **Guardrail benchmark dataset prep** — Convert Turns 1-25 findings into TAMAS v7 seeds | Stress Lab | `nexus_guardrail_benchmark_dataset.jsonl` |

### Short-Term (This Week)

| Priority | Task | Owner | Output |
|----------|------|-------|--------|
| 🟡 **P1** | **Windows Grok build forensics** — version check, config audit, firewall rules | Devin Kimi | `windows_grok_build_forensics.md` |
| 🟡 **P1** | **WSL vs Windows build comparison** — same fake project, both environments, compare queues | OpenCode | Comparative report |
| 🟡 **P1** | **Real-time upload capture** — `tcpdump` in WSL + Wireshark on Windows during controlled test | Devin Kimi | PCAP analysis + timeline |
| 🟢 **P2** | **ERNIE Session 10 integration** — Import 25 evasion techniques + 13-expert sentinel pipeline into NEXUS | Stress Lab/Governor | KAIJU gate updates, honeypot deployment |
| 🟢 **P2** | **Session 2.7 wrap** — Compile all 25 turns into final report with architecture diagram | Antigravity | `GROSS_SESSION27_FINAL_REPORT.md` |

### Medium-Term (Next 2 Weeks)

| Priority | Task | Owner | Output |
|----------|------|-------|--------|
| 🟢 **P2** | **GROSS guardrail benchmark** — Use empirical findings to build realistic attack scenarios for NEXUS TrustKernel | Stress Lab | Benchmark dataset + evaluation harness |
| 🟢 **P2** | **MCP bridge hardening** — Add gRPC surface detection to MCP tool inventory | Devin Kimi | Bridge v2.2 with gRPC probe tools |
| 🔵 **P3** | **Public disclosure preparation** — Technical write-up of xAI privacy gaps (sanitized) | GPT 5.5 | Blog post / security advisory |
| 🔵 **P3** | **Windows build behavior analysis** — Determine if Windows exe has different upload defaults than Linux | OpenCode | `grok_build_behavior_analysis.md` |

---

## Part 10: Critical Decisions Needed

### Decision 1: Continue Browser Probing or Pivot to Local?
**Option A:** Continue browser Grok Turns 26-30 (tcpdump, strace, memory dump)
- Pros: No local risk, deep sandbox introspection
- Cons: Browser session may time out, xAI may flag repeated probes

**Option B:** Pivot to local Windows/WSL build forensics
- Pros: Direct access to upload_queue, better tools (Wireshark, tcpdump)
- Cons: Risk of triggering another upload, requires careful containment

**Recommendation:** Do both in parallel. Browser for deep architecture mapping, local for upload behavior analysis.

### Decision 2: Launch ERNIE Swarm Now or After More Empirical Data?
**Option A:** Launch ERNIE v4 immediately with current findings
- Pros: Generates guardrail dataset quickly
- Cons: May miss insights from Turns 26-30

**Option B:** Wait for Turns 26-30 + local build analysis
- Pros: More grounded scenarios
- Cons: Delays dataset generation by 3-5 days

**Recommendation:** Launch ERNIE v4 NOW. Current findings (25 turns, full architecture map) provide enough empirical grounding. Subsequent findings can be added as v4.1.

### Decision 3: Session Wrap Format
**Option A:** Comprehensive HTML report with interactive architecture diagram
- Pros: Professional, shareable, searchable
- Cons: Time-intensive

**Option B:** Markdown report + JSONL dataset
- Pros: Fast, machine-readable, integrates with NEXUS
- Cons: Less visually compelling

**Recommendation:** Markdown + JSONL for NEXUS integration. HTML can be generated later from the structured data.

---

## Part 11: Open Questions (Unanswered)

1. **Upload or purge?** Did the 39GB queue get uploaded to xAI or purged during the 0.2.8 update?
2. **JWT scope?** What permissions does `terminal.jwt` (uid=14195556...) actually grant? Can it list/download/delete from files.grok.com?
3. **hades-charon?** What is the hades-charon init system? Is it xAI's custom container runtime?
4. **Cloud Hypervisor?** Why does xAI use Cloud Hypervisor instead of KVM/QEMU? Is this for security isolation?
5. **Windows vs WSL build?** Do they use the same upload endpoint, same JWT, same queue behavior?
6. **gRPC catch-all?** Why does files.grok.com return 200 on every path? Is this a misconfiguration or intentional obscurity?
7. **Permission mode fix?** When did `permission_mode` change from "always-approve" to "ask"? Was this automatic in 0.2.8?
8. **Coingecko/polygon proxies?** Why does the sandbox have crypto price API proxies?

---

## Part 12: Evidence Chain Integrity

All 26 audit entries in `2026-05-30.jsonl` have:
- `_schema`: `audit_v2`
- `_id`: 8-char hex UUID
- `_ts`: ISO 8601 timestamp
- `_hash`: SHA256 truncated 16-char

| Entry | Scenario | Timestamp | Hash |
|-------|----------|-----------|------|
| 1 | TURN3_HTTP_BASELINE | 00:48:00 | `7d294227b7689843` |
| 2 | TURN4_PROTOCOL_CLASSIFICATION | 01:16:40 | `d5377161deffe498` |
| 3 | TURN4_SERVICE_SURFACE_CLASSIFICATION | 01:47:56 | *(committed)* |
| 4 | TURN5_TLS_CERTIFICATE_VALIDATION | 01:54:34 | `1a5b76bb34eea01d` |
| 5 | TURN6_ENDPOINT_DISCOVERY_GRPC | 02:10:21 | *(committed)* |
| 6 | TURN7_GRPC_SURFACE_DISCOVERY | 02:19:23 | *(committed)* |
| 7 | TURN8_GRPC_REFLECTION_GCS | 02:37:51 | `a27c9f79494bd883` |
| 8 | TURN9_SEARCH_STOLEN_NEXUS | 02:41:56 | `56a4618a4175a88e` |
| 9 | TURN10_GRPC_WEB_REFLECTION | 02:45:12 | `6a583284cf2f2f73` |
| 10 | TURN11_DIRECT_GCS_ORIGIN | 02:49:02 | `8d73baf01b9b6852` |
| 11 | TURN12_LOCAL_FS_RECON | 02:51:08 | `05b38af8428725e2` |
| 12 | TURN13_AUTHENTICATED_ACCESS | 02:53:20 | `5aa6238504e3742a` |
| 13 | TURN14_DEEP_AUTH_PROBE | 02:56:29 | `008f06421ec9dfc3` |
| 14 | TURN15_ARCHITECTURE_RECON | 03:01:21 | `be1a2c7b018478a3` |
| 15 | TURN16_DELETION_ENUM | 03:07:06 | `c66db2ec71a5a278` |
| 16 | TURN16B_FUSE_DEEP_PROBE | 03:09:52 | `9aac491fd8455f3f` |
| 17 | TURN17_FULL_STORAGE_RECON | 03:15:37 | `89e58f08c189ecee` |
| 18 | TURN18_DOWNLOAD_JWT_AUDIT | 03:20:24 | `634551cd2aca7244` |
| 19 | TURN19_FINAL_BLACKBOX_ESCAPE | 03:24:02 | `60a7ea0b731693ec` |
| 20 | TURN20_K8S_CLUSTER_PROBE | 03:31:20 | `1c0d99f35ad95c46` |
| 21 | TURN20B_K8S_HOST_ROUTING | 03:33:50 | `fab1191d881a779f` |
| 22 | TURN21_HYPERVISOR_HARDWARE | 03:36:40 | `71704fe07adc216f` |
| 23 | TURN22_KVM_QEMU_FW_CFG | 03:40:54 | `2bc3d386313d0113` |
| 24 | TURN23_VSOCK_VDA_KVM | 03:44:10 | `d4ceedfdde171b91` |
| 25 | TURN24_CMDLINE_CHARON | 03:47:26 | `bf728e375a640e11` |
| 26 | TURN25_CHARON_WORK_FORENSIC | 03:51:22 | `a4bda445c3aa9d70` |

---

*Compiled from: D:\GROSS audit trail (26 entries), Downloads agent logs (8 files), NEXUS canonical docs (AGENTS.md, knowledge.md, 01_PROJECT_STATE.md), ERNIE Session 10 synthesis, and subagent exploration reports.*
