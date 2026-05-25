# TOOLS.md — Zo NEXUS Lane Guardian

**Version**: 4.0.0  
**Date**: 2026-05-25

---

## NETWORK & RELAY (VERIFIED WORKING)

| Endpoint | System | Status |
|----------|--------|--------|
| `http://127.0.0.1:18789` | OpenClaw Gateway (NIM) | ✅ LIVE |
| `https://specimba.zo.space/api/chat` | ModelRelay (NIM, English) | ✅ LIVE |
| `https://api.github.com` | GitHub (gh CLI) | ✅ AUTHENTICATED |
| Slack webhook | `#nexus-autoclaw` | ✅ CONNECTED |

---

## MODEL RELAY (zo.space)

**Base**: `https://specimba.zo.space`
**Chat endpoint**: `/api/chat`
**Health**: `/api/modelrelay/health`
**Models list**: `/api/modelrelay/models`

```bash
# Test
curl -s -X POST https://specimba.zo.space/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-ai/deepseek-v4-flash","messages":[{"role":"user","content":"say hello"}]}'
```

---

## OPENCLAW GATEWAY COMMANDS

```bash
openclaw status --deep        # Full status + model config
openclaw gateway probe        # Health check
openclaw security audit --deep # Security scan (0 crit, 0 warn)
openclaw config set gateway.controlUi.dangerouslyAllowPrivateNetworkAccess=true  # Enable if needed
```

**Health**: `curl -s http://127.0.0.1:18789/health` → `{"ok":true,"status":"live"}`

---

## WORKSPACE BOUNDARIES

| Path | Type | Notes |
|------|------|-------|
| `/home/workspace` | USER workspace | Write here — SPECI sees this |
| `/home/.z/workspaces/con_Q7zuyvaa7MyIV484` | Conversation workspace | Scratch only |
| `/root/.openclaw` | OpenClaw config | Root-owned |
| Zo Space routes | In-memory only | Not filesystem files |

---

## ZO COMPUTER TOOLS

| Tool | Use |
|------|-----|
| `run_bash_command` | Shell commands (Python, git, curl) |
| `create_or_rewrite_file` / `edit_file` | Text files in workspace |
| `write_space_route` / `edit_space_route` | zo.space API/page routes |
| `list_automations` / `create_automation` | Zo scheduled tasks |
| `list_user_services` / `update_user_service` | Long-running services |
| `use_app_gmail` / `use_app_slack` / etc. | Connected integrations |

---

## GITHUB WORKFLOW

```bash
gh api repos/specimba/NEXUS --json default_branch,description  # Query repo
gh api repos/specimba/nexus-mcp/contents/src  # Browse repo contents
git -C /home/workspace log --oneline -5  # Recent commits
git -C /home/workspace push github canonical-617  # Push branch
```

**Key repos**: NEXUS, nexus-mcp, nexus-mcp-search, DoppelGround, NEXUS-A2A-Operator, fastmcp

---

## GIT DISCIPLINE

- No `git add .` — stage explicit paths only
- Check `git status --short` before staging
- Commit: behavioral change + verification result
- Separate unrelated work into separate commits
- After commit: verify clean working tree

---

**Status**: ACTIVE  
**Owner**: Zo-NEXUS