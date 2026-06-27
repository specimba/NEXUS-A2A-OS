# Start a dedicated Chrome instance for the NEXUS Grok automation lane.
# Uses a SEPARATE user-data-dir so it never touches/locks your main Chrome profile.
# The NexusClaw Browser-AI Supervisor reads the authenticated Grok project tab via CDP.
#
# Run in your ADMIN terminal (not from an agent shell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_grok_cdp_9224.ps1
#
# Stop: close the Chrome window it opens, or kill the process.
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:USERPROFILE\.nexus_chrome_grok",
    [string]$StartUrl = "https://grok.com/project/99253cca-2469-4454-8593-0f173b7f640f"
)

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $chrome) { throw "Google Chrome not found. Install Chrome or set `$chrome manually." }
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

Write-Host "Starting Grok-lane Chrome (CDP :$Port, profile: $ProfileDir)"
Write-Host "  -> $StartUrl"
Write-Host "NOTE: dedicated profile. Log in to Grok ONCE in this window; the profile"
Write-Host "      persists, so you never log in again on later restarts."
Write-Host "Verify from any shell:  nexusctl grok-lane doctor   (cdp should be UP)"

Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts",
    $StartUrl
)

Start-Sleep -Seconds 2
try {
    $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 3
    Write-Host "[ok] CDP :$Port up -> $($r.Content.Substring(0,80))"
} catch {
    Write-Warning "CDP :$Port not reachable yet (Chrome may still be starting). Re-run: nexusctl grok-lane doctor"
}
