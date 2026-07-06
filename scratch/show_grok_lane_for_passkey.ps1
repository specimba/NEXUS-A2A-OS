# Stop hidden Grok CDP Chrome on 9224, reopen VISIBLE for passkey/WebAuthn.
$ErrorActionPreference = "Stop"
$Port = 9224
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

function Get-GrokLaneMainChrome {
    Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match "remote-debugging-port=$Port" -and
            $_.CommandLine -notmatch "--type="
        }
}

$mains = @(Get-GrokLaneMainChrome)
$profileDir = $null
if ($mains.Count -gt 0) {
    $cl = $mains[0].CommandLine
    if ($cl -match '--user-data-dir=([^\s"]+|"[^"]+")') {
        $profileDir = $Matches[1].Trim('"')
    }
    Write-Host "Stopping Grok-lane Chrome PID $($mains[0].ProcessId) ..."
    foreach ($p in $mains) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "No Chrome on CDP $Port; starting fresh visible window."
}

if (-not $profileDir) {
    $candidates = @(
        "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
        "$env:USERPROFILE\.nexus_chrome_grok"
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "Default\Login Data")) {
            $profileDir = $c
            Write-Host "Profile: $profileDir"
            break
        }
    }
    if (-not $profileDir) { $profileDir = "$env:USERPROFILE\.nexus_chrome_grok" }
}

$url = if ($env:NEXUS_GROK_PROJECT_CHAT_URL) { $env:NEXUS_GROK_PROJECT_CHAT_URL }
       elseif ($env:NEXUS_GROK_PROJECT_URL) { $env:NEXUS_GROK_PROJECT_URL }
       else { "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f?chat=4d8d8598-9da7-4639-918e-4ceb6a8812ba" }

Write-Host ""
Write-Host "=== VISIBLE Grok lane (passkey / WebAuthn) ==="
Write-Host "Profile: $profileDir"
Write-Host "URL:     $url"
Write-Host ""

& "$Repo\scripts\start_grok_cdp_9224.ps1" -ProfileDir $profileDir -Port $Port -ForceOpenGrokUrl

Start-Sleep -Seconds 2
$restore = Join-Path $Repo "tools\browser_ai_supervisor\grok_cdp_restore_window.mjs"
if (Test-Path $restore) {
    node $restore --port $Port --mode maximized
}