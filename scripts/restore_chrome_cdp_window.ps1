# Restore + optional foreground Chrome for NEXUS CDP lane (Win32 + browser-level CDP).
# Policy 2026-07-10: only force geometry when broken (offscreen / 1x1 / minimized).
# Never hide. Prefer -OnlyIfBroken -NoStealFocus so operator work is not interrupted.
param(
    [int]$Port = 9224,
    [string]$TitleContains = "Grok|Zo|ChatGPT|specimba|OpenAI|Chrome|Gemini|Qwen|DeepSeek|Meta|Intern|code-server",
    [switch]$SkipEnsure,
    [switch]$ForceShow,
    [switch]$Interactive,
    [switch]$OnlyIfBroken,
    [switch]$NoStealFocus,
    [switch]$NoMaximize
)

$ErrorActionPreference = "SilentlyContinue"
$repo = "C:\Users\speci.000\Documents\NEXUS"
if (-not $SkipEnsure) {
    $ensure = Join-Path $repo "scripts\ensure_cdp_lane_up.ps1"
    if (Test-Path $ensure) {
        & $ensure -Port $Port | Out-Null
    }
}

$wa = & "$repo\scripts\get_primary_work_area.ps1" | ConvertFrom-Json
$targetW = [Math]::Min(1280, $wa.width - 80)
$targetH = [Math]::Min(900, $wa.height - 80)
$targetX = $wa.left + [Math]::Max(40, [int](($wa.width - $targetW) / 2))
$targetY = $wa.top + [Math]::Max(40, [int](($wa.height - $targetH) / 2))

if (-not $ForceShow -and -not $Interactive) {
    Write-Host (ConvertTo-Json @{ status = "RESTORE_SKIPPED"; reason = "no_ForceShow_respect_operator"; port = $Port } -Compress)
    return
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class NativeWin {
  public const int SW_RESTORE = 9;
  public const int SW_SHOW = 5;
  public const int SW_MAXIMIZE = 3;
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool OpenIcon(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr Zero);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

$lanePids = @(
    Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
        Where-Object { $_.CommandLine -match "remote-debugging-port=$Port" } |
        Select-Object -ExpandProperty ProcessId
)

function Test-BrokenGeometry([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return $true }
    if ([NativeWin]::IsIconic($h)) { return $false }
    $rect = New-Object NativeWin+RECT
    if (-not [NativeWin]::GetWindowRect($h, [ref]$rect)) { return $true }
    $w = $rect.Right - $rect.Left
    $ht = $rect.Bottom - $rect.Top
    if (($ht -lt 200) -or ($w -lt 400) -or ($rect.Left -lt -500) -or ($rect.Top -lt -500) -or ($w -le 2) -or ($ht -le 2)) {
        if ([NativeWin]::IsIconic($h)) { return $false }
        return $true
    }
    return $false
}

function Fix-Geometry([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return $false }
    if (-not (Test-BrokenGeometry $h)) { return $false }
    [void][NativeWin]::MoveWindow($h, $targetX, $targetY, $targetW, $targetH, $true)
    return $true
}

function Show-Window([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return $false }
    $broken = Test-BrokenGeometry $h
    if ($OnlyIfBroken -and -not $broken) {
        return $false
    }
    [void](Fix-Geometry $h)
    if ([NativeWin]::IsIconic($h)) { [void][NativeWin]::OpenIcon($h) }
    [void][NativeWin]::ShowWindow($h, [NativeWin]::SW_SHOW)
    if ($Interactive -or $NoMaximize) {
        if ($broken) {
            [void][NativeWin]::MoveWindow($h, $targetX, $targetY, $targetW, $targetH, $true)
        }
    } else {
        # Only maximize when fixing a broken window — avoid fighting operator size
        if ($broken -and -not $OnlyIfBroken) {
            [void][NativeWin]::ShowWindow($h, [NativeWin]::SW_MAXIMIZE)
        } elseif ($broken) {
            [void][NativeWin]::MoveWindow($h, $targetX, $targetY, $targetW, $targetH, $true)
        }
    }
    if (-not $NoStealFocus) {
        [void][NativeWin]::BringWindowToTop($h)
        $fg = [NativeWin]::GetForegroundWindow()
        $fgTid = [NativeWin]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
        $wTid = [NativeWin]::GetWindowThreadProcessId($h, [IntPtr]::Zero)
        $cur = [NativeWin]::GetCurrentThreadId()
        if ($fgTid -ne $wTid) {
            [void][NativeWin]::AttachThreadInput($cur, $fgTid, $true)
            [void][NativeWin]::AttachThreadInput($cur, $wTid, $true)
        }
        $ok = [NativeWin]::SetForegroundWindow($h)
        if ($fgTid -ne $wTid) {
            [void][NativeWin]::AttachThreadInput($cur, $fgTid, $false)
            [void][NativeWin]::AttachThreadInput($cur, $wTid, $false)
        }
        return $ok
    }
    return $true
}

$restored = @()
$skippedOk = 0
$enum = [NativeWin+EnumWindowsProc]{
    param($hWnd, $lParam)
    $pid = 0
    [void][NativeWin]::GetWindowThreadProcessId($hWnd, [ref]$pid)
    if ($lanePids -notcontains $pid) { return $true }
    $title = New-Object System.Text.StringBuilder 512
    [void][NativeWin]::GetWindowText($hWnd, $title, 512)
    $t = $title.ToString()
    if ($TitleContains -and $t -notmatch $TitleContains -and $t.Length -lt 2) { return $true }
    if ($OnlyIfBroken -and -not (Test-BrokenGeometry $hWnd)) {
        $script:skippedOk++
        return $true
    }
    if (Show-Window $hWnd) { $script:restored += $pid }
    return $true
}
[void][NativeWin]::EnumWindows($enum, [IntPtr]::Zero)

Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.MainWindowHandle -ne 0 -and $lanePids -contains $_.Id) {
        if ($OnlyIfBroken -and -not (Test-BrokenGeometry $_.MainWindowHandle)) {
            $skippedOk++
            return
        }
        if (Show-Window $_.MainWindowHandle) { $restored += $_.Id }
    }
}

$browserRestore = Join-Path $repo "tools\browser_ai_supervisor\chrome_cdp_browser_restore.mjs"
if (Test-Path $browserRestore) {
    $brArgs = @(
        $browserRestore, "--port", $Port,
        "--work-left", $wa.left, "--work-top", $wa.top,
        "--work-width", $wa.width, "--work-height", $wa.height
    )
    if ($Interactive -or $NoMaximize) { $brArgs += "--interactive" }
    if ($OnlyIfBroken) { $brArgs += "--only-if-broken" }
    node @brArgs 2>&1
}

# Per-tab restore only when not OnlyIfBroken (avoids tab carousel / bringToFront spam)
if (-not $OnlyIfBroken) {
    $nodeRestore = Join-Path $repo "tools\browser_ai_supervisor\grok_cdp_restore_window.mjs"
    foreach ($match in @("grok.com", "zo.computer", "chatgpt.com")) {
        if (Test-Path $nodeRestore) {
            node $nodeRestore --port $Port --match $match --no-bring-to-front --mode normal 2>&1 | Out-Null
        }
    }
}

$restored = $restored | Select-Object -Unique
Write-Host (ConvertTo-Json @{
    status = if ($OnlyIfBroken -and $restored.Count -eq 0) { "OK_NO_FIX_NEEDED" } elseif ($Interactive) { "WIN32_RESTORE_INTERACTIVE" } else { "WIN32_RESTORE" }
    port = $Port
    pids = $restored
    skippedOk = $skippedOk
    onlyIfBroken = [bool]$OnlyIfBroken
    noStealFocus = [bool]$NoStealFocus
    target = @{ x = $targetX; y = $targetY; w = $targetW; h = $targetH }
    workArea = $wa
    interactive = [bool]$Interactive
    policy = "KEEP_VISIBLE_DEFAULT"
} -Compress)
