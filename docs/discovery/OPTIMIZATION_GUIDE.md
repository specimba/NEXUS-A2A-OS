# NEXUS OS — Optimization Guide & Refactoring Targets
## Version: 2026-06-09 (Updated with Session Findings)
## Priority: P0 (Immediate) → P3 (Long-term)

---

## ✅ COMPLETED IN THIS SESSION (2026-06-09)

| # | Fix | Status | Impact | Notes |
|---|-----|--------|--------|-------|
| 1 | **Security**: Moved sshkey.pem, env.txt, zilliz credentials to vault | ✅ Done | High | 7 sensitive files secured |
| 2 | **GPU Hog**: Increased ping intervals 1min → 5-60min | ✅ Done | High | GPU dropped from 45-53% to ~35% |
| 3 | **ARCHIVIST Index**: Created auto-generated index (1,590 files) | ✅ Done | High | `ARCHIVIST_INDEX.md` live |
| 4 | **NVIDIA Models**: Fixed model IDs, 14 now UP (was 0) | ✅ Done | High | API endpoint verified |
| 5 | **Intelligence Scores**: Updated with Arena + MMLU benchmarks | ✅ Done | High | DeepSeek 0.89, GPT-4o 0.81, GLM 5.1 0.90 |
| 6 | **Duplicate Scores**: Fixed kimi-k2.6 duplicate (0.87, not 0.76) | ✅ Done | Medium | Was being overwritten |
| 7 | **Archivist Wiki**: Built Karpathy-style wiki system | ✅ Done | High | 15 pages, 59,790 sources, boot.md for agents |
| 8 | **Boot Sync**: Created `boot.md` for 60-second agent onboarding | ✅ Done | High | Cross-platform compatible |
| 9 | **Smart Ping Design**: Documented demand-driven interval system | ✅ Done | Medium | `smart_ping_design.md` ready |
| 10 | **Garbage File**: Renamed corrupted filename | ✅ Done | Low | `29&(][11!34.txt` → `garbage_filename_corrupted.txt` |
| 11 | **Model Count**: 99 UP models (was 92), 225 total | ✅ Done | High | NVIDIA contributing 14 |

---

## 1. IMMEDIATE FIXES (P0 — Do Today)

### 1.1 Sanitize PII in deepseek_data
**Problem**: `deepseek_data-2026-05-06/conversations.json` may contain personal data
**Action**:
```bash
# 1. Review conversations.json for PII (names, emails, addresses)
# 2. If PII found, sanitize and overwrite
# 3. If no PII, add .gitignore to exclude from any git operations
# 4. Consider moving to encrypted vault or deleting if not needed
```
**Effort**: 30 minutes (review + sanitize)
**Impact**: Medium (privacy compliance)
**Status**: Pending

### 1.2 Fix Next.js Dashboard (Port 3000)
**Problem**: Port 3000 is occupied by WSL relay (`wslrelay.exe`), not Next.js dashboard
**Action**:
```bash
# Option A: Start Next.js on different port (e.g., 3001)
# Option B: Stop WSL relay and move it to different port
# Option C: Configure ModelRelay to use different port for UI
# Verify: curl http://localhost:3000 should return Next.js app, not WSL
```
**Effort**: 15-30 minutes
**Impact**: Medium (dashboard UI)
**Status**: Pending

### 1.3 Implement Smart Ping System (Phase 1)
**Problem**: Still burning API quotas even with increased intervals
**Action**: Create `smart_ping.py` that monitors port activity and adjusts intervals
```bash
# See: nexus_os/relay/smart_ping_design.md
# Create Python monitor, run alongside ModelRelay
python nexus_os/relay/smart_ping.py --daemon
```
**Effort**: 2-4 hours (Phase 1 Python script)
**Impact**: High (saves quotas, GPU, API costs)
**Status**: Design complete, ready for implementation

### 1.4 Fix Remaining NVIDIA 404s
**Problem**: 19 NVIDIA models still return 404 (mistral-large, ibm/granite, etc.)
**Root Cause**: These models exist in NVIDIA catalog but not at chat endpoint
**Action**:
```bash
# Check which models actually support chat completions at NVIDIA
# Some models are embeddings-only, vision-only, or safety models
# Remove non-chat models from sources.js or mark as non-chat
# Verify: curl -X POST https://integrate.api.nvidia.com/v1/chat/completions
```
**Effort**: 1 hour
**Impact**: Medium (clean up false DOWN models)
**Status**: Pending
**Action**: Generate `ARCHIVIST_INDEX.md` with:
- File list by category (plans, logs, code, research, configs)
- Last modified dates
- Duplicates identified
- Stale files flagged
- Critical files highlighted
```bash
# PowerShell:
Get-ChildItem -Recurse -File | Select-Object FullName, LastWriteTime, Length | Sort-Object LastWriteTime -Descending
```
**Effort**: 20 minutes (script + manual review)
**Impact**: High (productivity)

---

## 2. SHORT-TERM FIXES (P1 — This Week)

### 2.1 Log Rotation Policy
**Problem**: 61 log files in NEXUSlogs, no cleanup, consuming disk space
**Action**:
```powershell
# PowerShell script: nexus_log_rotate.ps1
$LogsDir = "C:\Users\speci.000\Downloads\NEXUSlogs"
$ArchiveDir = "C:\Users\speci.000\Downloads\NEXUSlogs\archive"
$MaxAgeDays = 30

# Move files older than 30 days to archive
# Compress archive monthly
# Keep last 30 days in active folder
```
**Effort**: 30 minutes
**Impact**: Medium (disk space, organization)

### 2.2 Fix NVIDIA Model IDs
**Problem**: All NVIDIA models return 404 (e.g., `deepseek-ai/deepseek-v3.2`)
**Root cause**: Model IDs may not match NVIDIA NIM catalog format
**Action**:
1. Check NVIDIA NIM catalog for correct model names
2. Update `sources.js` with correct IDs
3. Test one model: `curl http://localhost:7352/api/models` after restart
4. If all 50+ are wrong, batch-update via script
**Effort**: 1-2 hours (research + update)
**Impact**: Medium (would add ~50 UP models if fixed)

### 2.3 Google AI Recovery
**Problem**: 11 models DOWN, credits depleted (429)
**Options**:
- A: Add new Google AI API key to `.modelrelay.json`
- B: Switch to Google AI Studio free tier (different endpoint)
- C: Mark Google AI as deprecated, rely on other providers
**Effort**: 30 minutes (if key available) to 2 hours (if researching alternatives)
**Impact**: High (Gemini 2.5 Pro is 0.90 intelligence, would be top model if UP)

### 2.4 GitHub Models Recovery
**Problem**: 1500/day rate limit exceeded, ~5.6h cooldown
**Options**:
- A: Wait for cooldown (passive)
- B: Use different GitHub token (if available)
- C: Reduce polling frequency to stay under limit
- D: Mark as secondary provider, don't rely on it
**Effort**: 15 minutes (config change)
**Impact**: Low (GitHub models are mostly duplicates of other providers)

### 2.5 Verify Next.js Dashboard
**Problem**: Port 3000 may be offline
**Check**:
```bash
curl -s http://localhost:3000 | head -5
netstat -an | findstr "3000.*LISTENING"
```
**If offline**:
- Start from `nexus_os/dashboard/` or `src/` directory
- Check if `npm run dev` or `bun run dev` is needed
- Document startup procedure in MEMORY_INDEX
**Effort**: 30 minutes
**Impact**: Medium (main UI for human operators)

### 2.6 Archive Stale Implementation Plans
**Problem**: 17 implementation plans (01-17), most incomplete/abandoned, causing confusion
**Action**:
```bash
# Create archive directory
mkdir "C:\Users\speci.000\Downloads\ARCHIVIST\archive\implementation_plans"

# Move all implementation_plan*.md to archive
# Keep only the 2-3 most recent/relevant ones in active folder
# Add README in archive explaining why each was abandoned
```
**Effort**: 20 minutes
**Impact**: Medium (reduces clutter, confusion)

### 2.7 Delete Duplicate God Mode Proxy
**Problem**: `ARCHIVIST\NEXUS_god_mode_proxy.py` duplicates canonical `Documents\NEXUS\nexus_os\relay\god_mode_proxy.py`
**Risk**: If someone edits the wrong copy, changes won't apply
**Action**: Delete `ARCHIVIST\NEXUS_god_mode_proxy.py` and add a symlink or note pointing to canonical
**Effort**: 5 minutes
**Impact**: Low (prevents confusion)

---

## 3. MEDIUM-TERM IMPROVEMENTS (P2 — This Month)

### 3.1 Organize ARCHIVIST into Canonical Structure
**Current**: 283 flat files with garbage names
**Target**:
```
ARCHIVIST/
├─ active/                  ← Currently relevant files
├─ archive/                 ← Old but preserved
│  ├─ implementation_plans/
│  ├─ old_logs/
│  └─ deprecated/
├─ research/                ← Papers, model research
│  ├─ model_research/
│  └─ security_research/
├─ subsystems/              ← Code modules
│  ├─ modelrelay/
│  ├─ governor/
│  ├─ vault/
│  └─ team/
├─ configs/                 ← Configuration files
├─ logs/                    ← Log archives
└─ INDEX.md                 ← Master index
```
**Effort**: 2-3 hours (manual sorting + script)
**Impact**: High (findability, maintainability)

### 3.2 Implement Smart Health Checks
**Problem**: Current health check is brute-force (all models, all the time)
**Solution**: Demand-driven health checks
```python
class SmartHealthChecker:
    """Only check models when they're needed"""
    
    def check_model(self, model_id, reason="user_request"):
        """Check a specific model on demand"""
        # Only check if last check > 5 minutes ago
        # Skip if model is known DOWN and not in recovery window
        # Prioritize by user request > fallback chain > scheduled
        pass
    
    def scheduled_check(self, tier=3):
        """Only check tier-3 (reliable) providers on schedule"""
        # Check Mistral, Cloudflare, Groq every 5 minutes
        # Check tier-2 every 15 minutes
        # Check tier-1 every 60 minutes
        # Never check tier-0 (local, complex auth)
        pass
```
**Effort**: 2-3 hours (code + testing)
**Impact**: High (stops GPU burn, reduces API calls, saves quota)

### 3.3 Add Log Summarization Pipeline
**Problem**: 61 log files, hard to extract insights
**Solution**: Python script that:
1. Reads all .txt files in NEXUSlogs
2. Extracts error patterns, success rates, timing trends
3. Generates weekly summary report
4. Flags anomalies (e.g., sudden increase in errors)
```python
# nexus_log_summarizer.py
import glob, re
from collections import Counter, defaultdict

def summarize_logs(log_dir):
    errors = Counter()
    provider_status = defaultdict(lambda: {'up': 0, 'down': 0})
    # ... extract and summarize
    return summary_report
```
**Effort**: 3-4 hours
**Impact**: Medium (observability, proactive issue detection)

### 3.4 Expand GROSS Tool Coverage
**Current**: 17 MCP tools
**Opportunities** (from research):
- `verify_grok_config` — Check config.toml settings
- `monitor_network_connections` — Real-time TCP connection monitoring
- `scan_for_pii` — Check upload_queue for sensitive data
- `generate_legal_artifact` — Create evidence packages for legal use
- `compare_grok_versions` — Track version changes
- `test_privacy_opt_out` — Verify opt-out is working
- `monitor_registry_changes` — Watch Windows registry for Grok changes
**Effort**: 4-6 hours (per tool)
**Impact**: Medium (improves forensic capability)

### 3.5 Complete Phase 6: Always-Online MCP Server
**From PHASES_SUMMARY.md**: Build Docker-based MCP server on "zo computer"
**Status**: Not started
**Requirements**:
- Docker container running 24/7
- Exposes NEXUS OS tools via MCP protocol
- Connects to Telegram, Slack, Notion connectors
- Bridges semantic skills to system actions
- Governed by KAIJU/TrustKernel
**Effort**: 1-2 weeks (full implementation)
**Impact**: High (enables real automation, not just planning)

### 3.6 Implement Unified Model Score Verification
**Problem**: Intelligence scores are manually maintained, may drift from reality
**Solution**: Automated pipeline that:
1. Fetches latest MMLU/SWE-bench/Chatbot Arena scores from HF, arXiv, LMSYS
2. Updates `scores.js` automatically (with human review)
3. Flags models with no recent benchmark data
4. Version-controls score changes (VAP record)
```python
# score_verifier.py
import requests, json
from huggingface_hub import HfApi

def fetch_benchmarks(model_id):
    # Check HF model card for benchmark data
    # Check LMSYS Chatbot Arena for Elo
    # Check arXiv for recent papers
    return benchmark_scores
```
**Effort**: 1 week (research + implementation)
**Impact**: High (ensures routing decisions are based on real data)

---

## 4. LONG-TERM ARCHITECTURE (P3 — This Quarter)

### 4.1 Migrate Sensitive Data to Encrypted Vault
**Problem**: Secrets, keys, PII scattered across filesystem
**Target**: All sensitive data in `nexus_os/vault/` with:
- AES-256 encryption at rest
- Role-based access control
- Audit logging (who accessed what when)
- Automatic rotation reminders
**Effort**: 2-3 weeks
**Impact**: High (security compliance)

### 4.2 Automated ARCHIVIST Cleanup
**Problem**: ARCHIVIST will grow indefinitely (already 283 files)
**Solution**: Monthly automated job that:
1. Identifies files not accessed in 90 days
2. Moves to `archive/` directory
3. Compresses files > 1 year old
4. Flags duplicates for review
5. Generates cleanup report
**Effort**: 1 week (script + policy)
**Impact**: Medium (prevents bloat)

### 4.3 GROSS Automated Evidence Correlation
**Problem**: GROSS evidence is manually analyzed
**Solution**: Cross-agent consensus system that:
1. Ingests evidence from all agent logs (Codex, Grok, Devin, Kimi, etc.)
2. Correlates findings across sources
3. Flags discrepancies (e.g., one agent says "all clear", another says "anomaly")
4. Generates consensus report with confidence scores
5. Auto-escalates high-confidence findings
**Effort**: 2-3 weeks
**Impact**: High (reduces manual analysis, improves accuracy)

### 4.4 Unified Dashboard (Single Pane of Glass)
**Current**: Multiple dashboards (HTML on 7356, Next.js on 3000, possibly others)
**Target**: Single dashboard showing:
- Model health matrix (current 7356)
- GROSS audit status (confidential view)
- NEXUS logs summary
- System resource usage (GPU, RAM, disk)
- Agent activity timeline
- Task queue status
- Git repo status
**Effort**: 2-4 weeks
**Impact**: High (operational visibility)

### 4.5 Model Supply Chain Quarantine
**From implementation_plan17.md**: Block pickle/unsafe torch.load, trust_remote_code
**Implementation**:
- Scan all downloaded models for unsafe code
- Quarantine models with `trust_remote_code=True`
- Verify model signatures (SHA256 vs. known good)
- Block uncensored/red-team model labels from production
- Maintain allowlist of verified model sources
**Effort**: 1-2 weeks
**Impact**: High (security, prevents supply chain attacks)

### 4.6 A2A Protocol Completion
**From PHASES_SUMMARY.md**: Full agent-to-agent protocol
**Status**: Partial (connector-hub, telegram/slack/notion connectors exist)
**Remaining**:
- Agent card publication (`/.well-known/agent-card.json`)
- A2A message routing
- Cross-agent task delegation
- Capability negotiation
- Secure handshakes (mTLS)
**Effort**: 2-3 weeks
**Impact**: High (enables true multi-agent collaboration)

---

## 5. QUICK WINS (Low Effort, High Impact)

| # | Fix | Effort | Impact | File/Location |
|---|-----|--------|--------|---------------|
| 1 | Disable health check loop | 5 min | High | ModelRelay config |
| 2 | Move sshkey.pem to vault | 15 min | High | ARCHIVIST → vault |
| 3 | Delete duplicate proxy | 5 min | Low | ARCHIVIST cleanup |
| 4 | Archive old impl plans | 20 min | Medium | ARCHIVIST reorganization |
| 5 | Fix garbage filename | 5 min | Low | `29&(][11!34.txt` |
| 6 | Add .gitignore for logs | 5 min | Low | NEXUSlogs/ |
| 7 | Verify Next.js dashboard | 30 min | Medium | Port 3000 |
| 8 | Set OLLAMA_KEEP_ALIVE=0 | 5 min | High | Environment variable |
| 9 | Create ARCHIVIST_INDEX.md | 20 min | High | ARCHIVIST/ |
| 10 | Update MEMORY_INDEX.md | 10 min | Medium | docs/discovery/ |

---

## 6. METRICS & SUCCESS CRITERIA

### 6.1 Health Metrics (Target: 30 days)
- UP models: 92 → 120+ (fix NVIDIA, Google AI, Scaleway)
- Average latency: <1000ms for tier-3 providers
- GPU utilization: <30% (currently 45% due to health checks)
- Disk usage: <10GB for logs (implement rotation)
- Test pass rate: 617/617 → 650+/650+ (new tests)

### 6.2 Security Metrics (Target: 30 days)
- Sensitive files in Downloads: 2 → 0
- PII exposure incidents: 1 → 0
- GROSS queue size: <100KB (currently 21KB, good)
- Audit trail coverage: 80% → 95% of filesystem

### 6.3 Organization Metrics (Target: 30 days)
- ARCHIVIST files: 283 → <200 (archive stale, delete duplicates)
- Implementation plans: 17 → 3 (active only)
- Documentation freshness: 50% → 90% (<30 days old)
- Agent onboarding time: 60 min → 15 min (via MEMORY_INDEX)

---

## 7. VERIFICATION CHECKLIST

After each optimization, verify:
- [ ] Service restarted correctly (if applicable)
- [ ] Tests still pass (if code changed)
- [ ] Dashboard shows updated data
- [ ] God Mode Proxy routes correctly
- [ ] No sensitive data leaked in logs
- [ ] Git status clean (no unintended changes)
- [ ] MEMORY_INDEX updated (if structure changed)

---

*This is a living document. Add new targets as discovered. Mark completed items with [DONE] and date.*
