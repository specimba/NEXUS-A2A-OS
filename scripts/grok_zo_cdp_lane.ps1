# Dedicated Grok + Zo + ChatGPT CDP lane (do not mix with FABLE5 core).
param(
    [ValidateSet("Show", "Restore", "EnsureChrome", "StabilizeChrome", "FixChromeWindow", "RecoverChrome", "RestartChrome", "OpenCollabTabs", "OpenAllLanes", "RepairCanonicalUrls", "MimoClawBootstrap", "Probe", "Director", "Doctor", "ZoHint", "ChatGptHint", "SendZo", "SendGrok", "SendChatGPT", "NudgeGrok", "NudgeChatGPT", "WaitZo", "ListTabs", "CollabInventory", "CollabPlaytest", "A2AExperiment", "A2AExperimentObserve", "A2AExperimentLab", "StopA2AExperiment", "CoordinateLiveCollab")]
    [string]$Action = "Probe",
    [ValidateSet("continue", "proceed", "goon", "1", "2", "3", "A", "B", "C")]
    [string]$Nudge = "continue",
    [int]$Port = 9224,
    [switch]$RequiresBridge
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Repo

$profileDefault = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"
$node = "node"
$probe = Join-Path $Repo "tools\browser_ai_supervisor\grok_cdp_context_probe.mjs"
$restore = Join-Path $Repo "tools\browser_ai_supervisor\grok_cdp_restore_window.mjs"
$director = Join-Path $Repo "tools\browser_ai_supervisor\run_external_director.ps1"
$show = Join-Path $Repo "scratch\show_grok_lane_for_passkey.ps1"

switch ($Action) {
    "Show" {
        if (-not (Test-Path $show)) { throw "Missing $show" }
        & $show
    }
    "Restore" {
        & (Join-Path $Repo "scripts\ensure_lane_cdp.ps1") -Port $Port
        & (Join-Path $Repo "scripts\restore_chrome_cdp_window.ps1") -Port $Port -TitleContains "Grok|Zo|ChatGPT|specimba|OpenAI|Chrome" -SkipEnsure -ForceShow
    }
    "EnsureChrome" {
        & (Join-Path $Repo "scripts\ensure_lane_cdp.ps1") -Port $Port
    }
    "RestartChrome" {
        & (Join-Path $Repo "scripts\recover_lane_chrome.ps1") -Port $Port
    }
    "OpenCollabTabs" {
        & (Join-Path $Repo "scripts\open_all_browser_lanes.ps1") -Port $Port
    }
    "OpenAllLanes" {
        & (Join-Path $Repo "scripts\align_browser_lanes.ps1") -Port $Port
    }
    "RepairCanonicalUrls" {
        & (Join-Path $Repo "scripts\repair_canonical_lane_urls.ps1") -Port $Port
    }
    "StabilizeChrome" {
        & (Join-Path $Repo "scripts\fix_lane_chrome_interactive_window.ps1") -Port $Port
        & (Join-Path $Repo "scripts\align_browser_lanes.ps1") -Port $Port -SkipEnsure
    }
    "FixChromeWindow" {
        & (Join-Path $Repo "scripts\fix_lane_chrome_interactive_window.ps1") -Port $Port
    }
    "RecoverChrome" {
        & (Join-Path $Repo "scripts\recover_lane_chrome.ps1") -Port $Port
    }
    "MimoClawBootstrap" {
        & (Join-Path $Repo "scripts\ensure_lane_cdp.ps1") -Port $Port
        & $node (Join-Path $Repo "tools\browser_ai_supervisor\mimo_claw_bootstrap.mjs") --port $Port
    }
    "Probe" {
        & $node $probe --port $Port --required Grok --maxChars 3000
    }
    "Director" {
        $args = @("-RequiresBridge")
        if (-not $RequiresBridge) { $args = @() }
        & $director @args
    }
    "Doctor" {
        if (Get-Command nexusctl -ErrorAction SilentlyContinue) {
            nexusctl grok-lane doctor
        } else {
            & "$Repo\.venv\Scripts\python.exe" -m nexusctl.cli grok-lane doctor
        }
    }
    "ZoHint" {
        Write-Host "Zo chat:  $env:NEXUS_ZO_CHAT_URL"
        if (-not $env:NEXUS_ZO_CHAT_URL) {
            Write-Host "  default: https://specimba.zo.computer/?chat=con_EL8I2vKUvldsLVJ6"
        }
        Write-Host "Zo tunnel env:"
        Write-Host "  NEXUS_ZO_CDP_TUNNEL_URL=http://127.0.0.1:$Port  (after SSH -L)"
        Write-Host "  Windows CDP: http://127.0.0.1:$Port/json/version"
        Write-Host "  Doc: docs/operations/ZO_CDP_TUNNEL_WINDOWS_2026-07-02.md"
        Write-Host "  Git scope: docs/operations/GROK_ZO_CDP_LANE_GIT_SCOPE.md"
    }
    "ChatGptHint" {
        Write-Host "ChatGPT URL: $env:NEXUS_CHATGPT_CHAT_URL"
        if (-not $env:NEXUS_CHATGPT_CHAT_URL) {
            Write-Host "  default: https://chatgpt.com/c/6a4600ec-0db0-83eb-932c-9d3496adbba0 (GPT-5.5 agent thread)"
        }
        Write-Host "  Send: grok_zo_cdp_lane.ps1 -Action SendChatGPT"
    }
    "ListTabs" {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/json/list"
        $r | Where-Object { $_.type -eq "page" } | ForEach-Object {
            [PSCustomObject]@{ title = $_.title; url = ($_.url -replace '\?.*','?...') }
        } | Format-Table -AutoSize
    }
    "SendZo" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\send_zo_cdp.ps1") -Port $Port
    }
    "SendGrok" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\send_grok_cdp.ps1") -Port $Port `
            -PromptFile "tools\browser_ai_supervisor\prompts\hermes_zo_grok_handoff_short_v1.md"
    }
    "NudgeGrok" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\send_grok_cdp.ps1") -Port $Port -Nudge $Nudge
    }
    "WaitZo" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\wait_zo_idle_cdp.ps1") -Port $Port -MaxWaitSec 900
    }
    "SendChatGPT" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\send_chatgpt_cdp.ps1") -Port $Port
    }
    "NudgeChatGPT" {
        & (Join-Path $Repo "tools\browser_ai_supervisor\send_chatgpt_cdp.ps1") -Port $Port -SkipEnsure `
            -PromptFile "tools\browser_ai_supervisor\prompts\chatgpt\nudge_continue.md"
    }
    "CollabInventory" {
        & (Join-Path $Repo "scripts\collab_lane_playtest.ps1") -Port $Port
    }
    "CollabPlaytest" {
        & (Join-Path $Repo "scripts\collab_lane_playtest.ps1") -Port $Port -Send
    }
    "A2AExperiment" {
        Write-Warning "A2AExperiment is OBSERVE-ONLY (no CDP sends). Use A2AExperimentLab only on disposable lanes."
        & (Join-Path $Repo "scripts\coordinate_live_collab.ps1") -Port $Port -StopProcessId 0
    }
    "A2AExperimentObserve" {
        & (Join-Path $Repo "scripts\collab_lane_lock.ps1") -Mode on -Note "observe-only telemetry"
        & (Join-Path $Repo "scripts\start_a2a_long_run_experiment.ps1") -Port $Port -DurationMin 120 -CycleMin 15
    }
    "A2AExperimentLab" {
        & (Join-Path $Repo "scripts\collab_lane_lock.ps1") -Mode on -Note "lab mode - tri-lane still protected"
        & (Join-Path $Repo "scripts\start_a2a_long_run_experiment.ps1") -Port $Port -DurationMin 60 -CycleMin 15 -SendPings
    }
    "StopA2AExperiment" {
        & (Join-Path $Repo "scripts\stop_a2a_experiment.ps1")
    }
    "CoordinateLiveCollab" {
        & (Join-Path $Repo "scripts\coordinate_live_collab.ps1") -Port $Port
    }
}