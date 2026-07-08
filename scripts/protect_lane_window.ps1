param([int]$Port = 9224, [switch]$EnablePermanent, [string]$Guardrails = 'mythos')

$Repo = 'C:\Users\speci.000\Documents\NEXUS'
& "$Repo\scripts\fix_lane_chrome_interactive_window.ps1" -Port $Port | Out-Null

$lockDir = "$Repo\NEXUSlogs\a2a_experiment"
New-Item -ItemType Directory -Force -Path $lockDir | Out-Null

$protect = @{
    protected = $true
    at = (Get-Date).ToString('o')
    reason = 'permanent_no_auto_resize_collab'
    guardrails = $Guardrails
    permanent = [bool]$EnablePermanent
}
$protect | ConvertTo-Json | Set-Content "$lockDir\WINDOW_PROTECT.json" -Encoding UTF8

if ($EnablePermanent) {
    Write-Host 'Permanent mode enabled with Mythos guardrails (deliberation, CDP bounds, prefs lock).'
}
Write-Host 'Window protection enhanced.'