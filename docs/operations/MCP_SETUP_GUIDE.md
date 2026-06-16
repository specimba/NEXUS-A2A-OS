---
id: NODE-MIG-MCP_SETUP_GUIDE
authority_scope: experimental
origin_sha256: 51a28a1069715701fe98159c97b009dfc9028b0fe4f72f923683c0a91a968508
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-F1C7C3
---
# NEXUS OS MCP Profile Setup Guide

## Overview

You now have a fully configured MCP (Model Context Protocol) profile optimized for NEXUS OS v4 multi-agent governance system. This profile integrates:

- **Governance**: KAIJU gates, VAP chain, TokenGuard, cross-agent security
- **Infrastructure**: Docker, Kubernetes, WSL2 sandbox orchestration
- **Data**: Neo4j knowledge graph, PostgreSQL, Zilliz vector memory, Supabase
- **Inference**: vLLM local, OpenAI/OpenRouter, AWS Bedrock, HuggingFace Sandbox
- **Communication**: Slack bot network, GitHub automation, email delivery
- **Research**: Web crawling (Browserbase), documentation lookup (Ref Tools)

---

## Files Created

### 1. **`mcp_profile_nexus_os_v4.json`** (Main Profile)
Location: `C:\Users\speci.000\Documents\NEXUS\mcp_profile_nexus_os_v4.json`

Comprehensive MCP configuration with:
- 20+ MCP servers (Neo4j, Docker, Kubernetes, GitHub, Slack, vLLM, Zilliz, etc.)
- 9 client integrations (Claude Desktop, Cursor, Cline, Continue.dev, etc.)
- 4-tier deployment strategy (Local → Sandbox → Kubernetes → Cloud)
- Governance settings (KAIJU, VAP, hallucination detection, terminal sanitizer)
- Speculative decoding configuration (MARS + Lookahead + N-gram)

**Status**: ✅ Ready to use

---

### 2. **`claude_desktop_config.json`** (Claude Desktop Config)
Location: `C:\Users\speci.000\AppData\Roaming\Claude\claude_desktop_config.json`

Configured with core MCP servers:
- `neo4j` — Knowledge graph queries
- `docker` — Compose orchestration
- `github` — PR/issue management
- `slack` — Bot integration
- `postgres` — Database queries
- `sqlite` — Local data
- `filesystem` — File access
- `python-repl` — Code execution
- `bash` — Shell commands

**How to activate**: Close and reopen Claude Desktop. It will auto-load this config.

**Status**: ✅ Installed

---

### 3. **`mcp_config.json`** (Cursor Config)
Location: `C:\Users\speci.000\AppData\Roaming\Cursor\mcp_config.json`

Lightweight config optimized for code editing:
- GitHub (PR/branch management)
- Docker (compose orchestration)
- Filesystem (project navigation)
- Postgres (schema inspection)
- Python REPL (inline execution)

**How to activate**: Restart Cursor. Open settings → MCP and verify servers appear.

**Status**: ✅ Installed

---

## Installation Steps

### For Claude Desktop

1. **Verify installation**:
   ```powershell
   Test-Path "$env:APPDATA\Claude\claude_desktop_config.json"
   ```
   Should output: `True`

2. **Restart Claude Desktop** (full close + reopen, not just minimize).

3. **Verify MCP servers are loading**:
   - Open Claude Desktop console (Ctrl+Shift+I or Cmd+Opt+I on Mac)
   - Look for "MCP servers initialized" messages
   - No errors about missing commands like `docker`, `npx`, `python`

4. **Test a server**:
   - Ask Claude: "List my GitHub repos"
   - Or: "Show me the Docker containers currently running"

---

### For Cursor

1. **Create config directory if missing**:
   ```powershell
   mkdir "$env:APPDATA\Cursor" -Force
   ```

2. **Restart Cursor**.

3. **Open Cursor settings**:
   - Ctrl+Shift+P → "MCP" or "Settings"
   - You should see MCP servers listed

4. **Test**:
   - Open a Python file and ask Cursor for help with syntax
   - Ask it to check your GitHub repos

---

### For Cline

Cline uses Claude Desktop's config. Once Claude is set up, Cline will inherit the MCP servers.

**To force reload**:
```powershell
# Inside VS Code with Cline extension:
# Restart VS Code, Cline will re-initialize
```

---

## Troubleshooting

### Problem: "MCP server failed to start"

**Check prerequisites**:
```powershell
# Verify Node.js is installed
node --version   # Should be v16+

# Verify npm is available
npm --version    # Should be v7+

# Verify Docker is running
docker --version
docker ps

# Verify Python is in PATH
python --version  # Should be 3.10+
```

If any of these fail, install them or add to PATH:
```powershell
# Add Node to PATH (if installed but not in PATH)
$env:PATH += ";C:\Program Files\nodejs"

# Add Python to PATH
$env:PATH += ";C:\Users\speci.000\AppData\Local\Programs\Python\Python310"
```

---

### Problem: "github server failed" or "docker server failed"

**Check environment variables**:
```powershell
# These must be set in your .env or system environment
$env:GITHUB_PAT_KEY
$env:DATABASE_URL
$env:SLACK_BOT_TOKEN  # If using Slack server

# If blank, export them:
$env:GITHUB_PAT_KEY = "your_token_here"
```

**Restart Claude/Cursor after setting env vars**.

---

### Problem: "Docker permission denied" or "daemon not running"

**On Windows**:
```powershell
# Make sure Docker Desktop is running
Get-Process "Docker Desktop" -ErrorAction SilentlyContinue

# If not running, start it:
& "C:\Program Files\Docker\Docker\Docker.exe"

# Or via WSL2:
wsl --list --verbose
```

---

### Problem: "Neo4j connection refused"

**Start Neo4j container**:
```powershell
docker-compose up -d neo4j  # From your NEXUS project
```

---

### Problem: Silent failure (MCP server starts but produces no output)

**Check logs**:

**Claude Desktop**:
- Open DevTools: Ctrl+Shift+I
- Look for "mcp" in console
- Check for errors in "Network" tab if using remote servers

**Cursor**:
- Open Output panel (Ctrl+Shift+U)
- Select "MCP" from dropdown

---

## Usage Examples

### 1. Query Your Knowledge Graph (Neo4j)

**Prompt**: "Show me all agents in the NEXUS governance graph and their trust scores"

Claude will query Neo4j and return relationships like:
```
Agent: Pi → Trust: 0.85 → Permissions: CODE_EXECUTION, SANDBOX_ESCAPE
Agent: Codex → Trust: 0.92 → Permissions: CODE_REVIEW, ARCHITECTURE
Agent: Kilo → Trust: 0.88 → Permissions: SECURITY_SCAN
```

---

### 2. Manage GitHub PRs

**Prompt**: "Create a GitHub issue for the NEXUS repo with title 'Add MARS speculative decoding' and assign it to me"

Claude will create the issue and return the GitHub link.

---

### 3. Execute Docker Compose

**Prompt**: "Start the Supabase stack and show me the container status"

Claude will run:
```bash
docker-compose up -d supabase
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

### 4. Query Vector Memory (Zilliz)

**Prompt**: "Search my vector memory for hallucination patterns in recent VAP chain entries"

Claude will query Zilliz and return semantic matches from your governance logs.

---

### 5. Run Python Code

**Prompt**: "Write a Python script to analyze my NEXUS token usage patterns from the last 7 days"

Claude will generate code, execute it via Python REPL, and show results.

---

## Advanced Configuration

### Adding New MCP Servers

1. **Edit** `C:\Users\speci.000\Documents\NEXUS\mcp_profile_nexus_os_v4.json`

2. **Add a new server** (example: Jira):
   ```json
   "jira": {
     "command": "npx",
     "args": ["-y", "@modelcontextprotocol/server-jira"],
     "env": {
       "JIRA_HOST": "https://your-instance.atlassian.net",
       "JIRA_EMAIL": "your-email@example.com",
       "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
     },
     "disabled": false,
     "priority": 8,
     "description": "Jira issue tracking for NEXUS ops"
   }
   ```

3. **Add to client** (Claude Desktop example):
   ```json
   "mcpServers": {
     "jira": { ... },
     // existing servers...
   }
   ```

4. **Restart Claude Desktop**.

---

### Tier-Specific Configurations

**For Local Development Only** (Tier 1):
Use only: `vllm-local`, `github`, `ref-tools`, `openai-relay`

**For Full Sandbox Testing** (Tier 2):
Add: `docker`, `postgres`, `supabase`, `zilliz`

**For Kubernetes Deployment** (Tier 3):
Add: `kubernetes`, `render`, `aws-bedrock`

**For Cloud Burst** (Tier 4):
Add: `hf-sandbox`, `aws-pricing`, full `aws-bedrock`

---

## Integration with Slack (@Zo Orchestrator)

Once Slack MCP is active, you can:

1. **Post to Slack from Claude**:
   ```
   Post to #nexus-control: "Task: Review PR #42. Assigned to @Codex"
   ```

2. **Trigger agent workflows**:
   ```
   @Zo: Route this task to @Devin for code review and @Sanity for validation
   ```

3. **Monitor Slack channels from Claude**:
   ```
   Show me unread messages in #nexus-codex-tasks from the last 2 hours
   ```

---

## Performance Tuning

### Speculative Decoding Settings

Configured in the profile as:
```json
"inference": {
  "speculative_decoding": {
    "method": "mars_lookahead_ngram",
    "target_speedup": "2.5x",
    "margin_threshold": 0.15
  }
}
```

**If inference is slow**:
- Lower `margin_threshold` to 0.10 (stricter verification, fewer rejections)
- Switch `method` to `"ngram"` (fastest but lowest quality)

**If hallucinations increase**:
- Raise `margin_threshold` to 0.20 (looser verification, more safety checks)
- Enable `cross_agent_verification` (double-check outputs)

---

## Security Checklist

✅ **Safety features enabled**:
- KAIJU gates (autonomy approval)
- VAP chain logging (immutable audit trail)
- Cross-agent verification (prompt injection defense)
- Output sanitization (terminal escape stripping)
- Hallucination detection (3-layer checks)

✅ **Credentials**:
- All API keys stored in `.env` (not in config)
- Config file uses `${VAR_NAME}` syntax (environment interpolation)
- Commit only `.env.example` to GitHub, not `.env`

✅ **Isolation**:
- All agent execution in disposable Docker containers
- No persistent filesystem access to host
- Network policies enforced per sandbox

---

## Next Steps

1. **Test Claude Desktop** with a simple query:
   ```
   "List my GitHub repos and show the last 3 commits from each"
   ```

2. **Enable Slack integration** by creating a Slack bot:
   - Go to your Slack workspace → Settings → Apps
   - Create a new bot app
   - Generate API tokens
   - Set `SLACK_BOT_TOKEN` and `SLACK_WEBHOOK_URL` in `.env`

3. **Start Supabase & Neo4j**:
   ```powershell
   cd C:\Users\speci.000\Documents\NEXUS
   docker-compose up -d postgres neo4j supabase
   ```

4. **Boot NEXUS governance**:
   ```powershell
   python -m nexus_os.boot
   ```

5. **Monitor in Slack**:
   - @Zo will post governance decisions to #nexus-control
   - Agents will report status in respective channels

---

## Support

If MCP servers fail to load:

1. **Check Claude Desktop logs**:
   ```powershell
   # Windows
   cat "$env:APPDATA\Claude\logs\*.log"
   ```

2. **Restart everything**:
   ```powershell
   # Kill all Node/Python MCP processes
   Get-Process node, python | Stop-Process -Force
   
   # Restart Claude
   ```

3. **Verify dependencies**:
   ```powershell
   npm list -g @modelcontextprotocol
   python -m pip list | Select-String mcp
   ```

---

**Profile created**: 2026-05-20  
**NEXUS OS version**: 4.0  
**MCP protocol version**: 1.0  
**Status**: ✅ Production-ready
