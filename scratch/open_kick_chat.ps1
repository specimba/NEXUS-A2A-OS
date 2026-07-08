$ErrorActionPreference = 'SilentlyContinue'
$url = 'https://kick.com/popout/specimba/chat'

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KickWin {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
}
"@

$focused = $false
Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {
  if ($_.MainWindowHandle -eq 0) { return }
  if ($_.MainWindowTitle -notmatch 'kick\.com') { return }
  $h = $_.MainWindowHandle
  if ([KickWin]::IsIconic($h)) { [void][KickWin]::ShowWindow($h, 9) }
  [void][KickWin]::ShowWindow($h, 3)
  [void][KickWin]::SetForegroundWindow($h)
  Write-Output ('FOCUSED pid=' + $_.Id + ' title=' + $_.MainWindowTitle)
  $focused = $true
}

if ($focused) { exit 0 }

foreach ($p in 9222,9223,9224,9225,9226) {
  try {
    $tabs = Invoke-RestMethod -Uri "http://127.0.0.1:$p/json/list" -TimeoutSec 2
    $kick = $tabs | Where-Object { $_.type -eq 'page' -and $_.url -match 'kick\.com' } | Select-Object -First 1
    if (-not $kick) { continue }
    $repo = 'C:\Users\speci.000\Documents\NEXUS'
    $restore = Join-Path $repo 'tools\browser_ai_supervisor\grok_cdp_restore_window.mjs'
    if (Test-Path $restore) {
      node $restore --port $p --match 'kick\.com' --mode maximized
    }
    Write-Output ('CDP_RESTORE port=' + $p + ' title=' + $kick.title)
    exit 0
  } catch {}
}

$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $chrome) { Write-Error 'Chrome not found'; exit 1 }
Start-Process -FilePath $chrome -ArgumentList @($url, '--new-window')
Write-Output ('LAUNCHED ' + $url)