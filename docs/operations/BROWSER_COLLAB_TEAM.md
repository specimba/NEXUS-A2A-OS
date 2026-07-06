# Browser collab team (CDP :9224)

| Player | Tab match | Pace | Hermes action |
|--------|-----------|------|----------------|
| **Grok** | `grok.com` | Fast; nudge `continue` / `2` / `B` | `NudgeGrok`, `SendGrok` |
| **Zo** | `zo.computer` | Long-run; wait idle | `SendZo`, `WaitZo` |
| **ChatGPT** | `chatgpt.com` | Senior review; 2-4 turns | `SendChatGPT`, `NudgeChatGPT` |

## Chrome ghost window (taskbar click does nothing)

1. `.\scripts\grok_zo_cdp_lane.ps1 -Action Restore`
2. If still broken: `.\scripts\grok_zo_cdp_lane.ps1 -Action RestartChrome`

Restore stack: `chrome_cdp_browser_restore.mjs` (Browser.setWindowBounds) + Win32 EnumWindows + AttachThreadInput foreground.

## ChatGPT setup

Set your thread (GPT-5.x session):

```powershell
$env:NEXUS_CHATGPT_CHAT_URL = "https://chatgpt.com/c/YOUR-THREAD-ID"
.\scripts\grok_zo_cdp_lane.ps1 -Action RestartChrome
.\scripts\grok_zo_cdp_lane.ps1 -Action SendChatGPT
```

Tag: `[CHATGPT-PLAN]` in replies.

See also `CDP_LANE_CONVERSATION_STYLES.md`.