param([int]$Port = 9224)
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo
$env:NEXUS_CHATGPT_CHAT_URL = "https://chatgpt.com/"
& "$Repo\scripts\grok_zo_cdp_lane.ps1" -Action Restore
& "$Repo\scripts\grok_zo_cdp_lane.ps1" -Action OpenCollabTabs -Port $Port
& "$Repo\tools\browser_ai_supervisor\send_chatgpt_cdp.ps1" -SkipEnsure -PromptFile "tools\browser_ai_supervisor\prompts\chatgpt\hermes_collab_mcp_new_chat_v1.md"