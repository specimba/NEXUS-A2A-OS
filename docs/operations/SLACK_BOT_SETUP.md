---
id: NODE-MIG-SLACK_BOT_SETUP
authority_scope: experimental
origin_sha256: ae3e2150bb1b70efff52820a98121ac943724b4b4404e2af4170fe3556bedf22
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-7605C8
---
# Slack Bot Configuration for @Zo Orchestrator

This file documents how to set up the Slack bot network for NEXUS OS.

## Prerequisites

1. Slack workspace admin access
2. Ability to create Slack apps
3. `SLACK_BOT_TOKEN` and `SLACK_WEBHOOK_URL` from your Slack app

---

## Step 1: Create Slack App

1. Go to: https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. **App name**: `NEXUS Orchestrator`
4. **Pick a workspace**: Your NEXUS workspace
5. Click **"Create App"**

---

## Step 2: Enable Permissions

In your app settings:

1. Navigate to **"OAuth & Permissions"** (left sidebar)

2. Under **"Scopes"**, add these **Bot Token Scopes**:
   ```
   chat:write
   chat:write.public
   chat:write.customize
   channels:read
   users:read
   files:write
   reactions:write
   commands:write
   app_mentions:read
   messages:read
   im:read
   groups:read
   mpim:read
   pins:write
   files:read
   ```

3. Scroll to top → **"Install to Workspace"** or **"Reinstall to Workspace"**

4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
   - Set as: `SLACK_BOT_TOKEN=xoxb-...` in your `.env`

---

## Step 3: Enable Webhooks

1. In your Slack app dashboard, go to **"Incoming Webhooks"**
2. Toggle **"Activate Incoming Webhooks"** to ON
3. Click **"Add New Webhook to Workspace"**
4. Select channel: `#nexus-control` (or create it)
5. Click **"Allow"**
6. Copy the **Webhook URL** (starts with `https://hooks.slack.com/...`)
   - Set as: `SLACK_WEBHOOK_URL=https://...` in your `.env`

---

## Step 4: Configure Event Subscriptions

For real-time bot responses:

1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. For **"Request URL"**, enter: `https://your-nexus-api.com/slack/events`
   - (Update with your actual NEXUS API endpoint)
4. Slack will verify the URL
5. Under **"Subscribe to bot events"**, add:
   ```
   app_mention
   message.channels
   message.groups
   message.im
   ```

---

## Step 5: Configure Slash Commands

Create commands for manual task routing:

### Command 1: `/nexus-task`

1. Go to **"Slash Commands"**
2. Click **"Create New Command"**
   - **Command**: `/nexus-task`
   - **Request URL**: `https://your-nexus-api.com/slack/commands/task`
   - **Short Description**: "Route a task to an agent"
   - **Usage hint**: `@agent action "details"`

### Command 2: `/nexus-status`

1. Click **"Create New Command"** again
   - **Command**: `/nexus-status`
   - **Request URL**: `https://your-nexus-api.com/slack/commands/status`
   - **Short Description**: "Show NEXUS system status"
   - **Usage hint**: `[component]`

### Command 3: `/nexus-logs`

1. Click **"Create New Command"** again
   - **Command**: `/nexus-logs`
   - **Request URL**: `https://your-nexus-api.com/slack/commands/logs`
   - **Short Description**: "View VAP chain audit logs"
   - **Usage hint**: `[agent_id] [--last N hours]`

---

## Step 6: Set Up Channels

Create these Slack channels (if not existing):

```powershell
# Using Slack API or manually in Slack:

#nexus-control          (PRIVATE) - Governance decisions, task intake
#nexus-codex-tasks      (PRIVATE) - Code review assignments
#nexus-reviews          (PUBLIC) - Review summaries, approvals
#nexus-research         (PUBLIC) - Research findings
#nexus-ops              (PRIVATE) - Incidents, alerts
#all-nexus-os           (PUBLIC) - Announcements, digests
```

---

## Step 7: Configure Claude/Cursor to Use Slack MCP

In your `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_APP_ID=A0000000000
```

Restart Claude Desktop or Cursor.

Test:
```
Ask Claude: "Post a message to #nexus-control: 'System initialized'"
```

---

## Step 8: Configure Bot Identity

In `C:\Users\speci.000\Documents\NEXUS\.env`:

```env
# Slack Bot Identities
SLACK_BOT_ZO_ID=U0000ZO000
SLACK_BOT_DEVIN_ID=U0000DEV00
SLACK_BOT_CODEX_ID=U0000COD00
SLACK_BOT_KILO_ID=U0000KIL00
SLACK_BOT_SANITY_ID=U0000SAT00

# Bot display names
SLACK_BOT_NAME_PRIMARY=@Zo
SLACK_BOT_NAME_CODE_REVIEWER=@Devin
SLACK_BOT_NAME_ARCH_REVIEWER=@Codex
SLACK_BOT_NAME_SECURITY=@Kilo
SLACK_BOT_NAME_VALIDATION=@Sanity
```

---

## Testing the Slack Integration

### Test 1: Direct Message

Ask Claude:
```
Send a direct message to @Zo: "NEXUS system initialized"
```

Expected: Claude posts to `@zo` in Slack.

---

### Test 2: Channel Post

Ask Claude:
```
Post to #nexus-control: "Task assigned: Code review for PR #42"
```

Expected: Message appears in `#nexus-control` with timestamp.

---

### Test 3: Slash Command

In Slack:
```
/nexus-status
```

Expected: NEXUS responds with system health, token budget, active tasks.

---

### Test 4: Multi-Bot Coordination

Ask Claude:
```
Route task to @Codex: "Review the NEXUS_OS_V4_MASTER_PLAN.md architecture"
```

Expected:
1. Claude posts to `#nexus-codex-tasks`: "Task assigned to @Codex"
2. @Codex (another AI agent) reads the task from Slack
3. @Codex returns review to `#nexus-reviews`
4. Claude summarizes in `#nexus-control`

---

## Troubleshooting Slack Integration

### Problem: "Slack connection failed" or "invalid_token"

1. Verify `SLACK_BOT_TOKEN` is correct:
   ```powershell
   $env:SLACK_BOT_TOKEN
   ```

2. Check token permissions in Slack app dashboard:
   - Go to **"OAuth & Permissions"**
   - Verify bot has `chat:write`, `channels:read`, etc.

3. Regenerate token if expired:
   - **"OAuth & Permissions"** → **"Reinstall to Workspace"**
   - Copy new token to `.env`

4. Restart Claude:
   ```powershell
   # Kill Claude and reopen
   Get-Process "Claude" | Stop-Process -Force
   ```

---

### Problem: "Webhook URL invalid" or "not reachable"

1. Verify webhook URL is correct:
   ```powershell
   $env:SLACK_WEBHOOK_URL
   ```

2. Test manually:
   ```powershell
   $payload = @{text="Test message"} | ConvertTo-Json
   Invoke-RestMethod -Uri $env:SLACK_WEBHOOK_URL -Method Post -Body $payload -ContentType "application/json"
   ```

3. If request fails, check:
   - Firewall blocking HTTPS to `hooks.slack.com`
   - Webhook URL expired (regenerate in Slack app settings)
   - Network connectivity

---

### Problem: "App not responding to slash commands"

1. Verify **"Request URL"** in Slash Commands matches your API endpoint
2. Check that your NEXUS API is running on the correct port (usually 8000 or 3000)
3. Review **"Event Subscriptions"** → ensure they're enabled and verified

---

## Advanced: Bot Workflows

Once set up, you can trigger complex workflows:

### Workflow: Automated Code Review

```
1. User: "Review PR #42"
2. Slack: @Codex routed the task
3. @Codex (AI): Reads PR diff, generates review in #nexus-reviews
4. @Sanity (AI): Validates code review quality
5. Slack: Summary posted to #nexus-control with approval/rejection
6. @Zo (orchestrator): Logs decision in VAP chain
```

### Workflow: Security Scanning

```
1. Trigger: New PR merged to main
2. GitHub webhook → Slack: #nexus-codex-tasks "New PR merged: ..."
3. @Kilo (security scanner): Scans codebase, checks for vulnerabilities
4. Slack: #nexus-reviews "Security scan complete: 0 critical, 2 warnings"
5. If critical: @Zo pauses deployment, escalates to #nexus-ops
```

---

## Next Steps

1. **Complete this setup** by running:
   ```powershell
   cd C:\Users\speci.000\Documents\NEXUS
   python scripts/setup_slack_bots.py
   ```

2. **Test in Slack** with simple commands
3. **Enable bot identities** (Devin, Codex, Kilo) once Claude integration works
4. **Set up GitHub webhook** to feed PR events to Slack

---

**Last updated**: 2026-05-20  
**NEXUS version**: 4.0  
**Slack API version**: v1.0
