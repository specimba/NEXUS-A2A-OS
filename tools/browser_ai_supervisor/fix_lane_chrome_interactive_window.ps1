# fix_lane_chrome_interactive_window.ps1
# Manual-only helper for making specific CDP lane Chrome windows visible and foregrounded.
# Run manually: .\scripts\fix_lane_chrome_interactive_window.ps1 -ManualObservation [-KeepVisible] [-PollSeconds 2]
param(
    [int]$Port = 9224,
    [switch]$ManualObservation,
    [switch]$KeepVisible,
    [int]$PollSeconds = 2
)

if (-not $ManualObservation -and $env:NEXUS_ALLOW_FOREGROUND_LANE_REPAIR -ne "1") {
    Write-Warning "Foreground lane repair is manual-only. Re-run with -ManualObservation or set NEXUS_ALLOW_FOREGROUND_LANE_REPAIR=1. Autonomous supervisors must use the hidden/offscreen launcher."
    exit 3
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
}
"@
$SW_RESTORE = 9
$SW_SHOW = 5
$SWP_NOMOVE = 0x0002
$SWP_NOSIZE = 0x0001
$HWND_TOP = [IntPtr]0

$lanePatterns = 'Nexus|Gemini|Qwen|DeepSeek|ChatGPT|Grok|NEXUS|Meta|Muse|ai|Collab|Browser'

function Restore-Lanes {
    $count = 0
    Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {
        $title = $_.MainWindowTitle
        if ($title -and ($title -match $lanePatterns)) {
            $h = $_.MainWindowHandle
            if ($h -ne 0) {
                if ([Win32]::IsIconic($h)) { [Win32]::ShowWindow($h, $SW_RESTORE) | Out-Null }
                [Win32]::ShowWindow($h, $SW_SHOW) | Out-Null
                [Win32]::SetForegroundWindow($h) | Out-Null
                [Win32]::SetWindowPos($h, $HWND_TOP, 0, 0, 0, 0, $SWP_NOMOVE -bor $SWP_NOSIZE) | Out-Null
                Write-Host "Restored + foregrounded: $title (PID $($_.Id), CDP port hint $Port)"
                $count++
            }
        }
    }
    if ($count -eq 0) { Write-Warning "No matching lane windows found. Ensure Chrome is running with remote debugging on $Port and tabs match the patterns." }
    return $count
}

function Restore-LanesViaCdp {
    # When MainWindowTitle is empty (common for --remote-debugging Chrome),
    # Win32 restore finds nothing. Fall back to CDP Browser.setWindowBounds
    # via the existing operator restore helper (Grok match by default).
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        Write-Warning "node not on PATH; cannot CDP-restore windows."
        return 0
    }
    $restoreJs = Join-Path $PSScriptRoot "grok_cdp_restore_window.mjs"
    if (-not (Test-Path $restoreJs)) {
        $restoreJs = Join-Path $PSScriptRoot "..\..\tools\browser_ai_supervisor\grok_cdp_restore_window.mjs"
    }
    if (-not (Test-Path $restoreJs)) {
        Write-Warning "grok_cdp_restore_window.mjs not found for CDP fallback."
        return 0
    }
    $matches = @("grok\\.com", "gemini\\.google\\.com", "chat\\.qwen\\.ai", "chatgpt\\.com", "meta\\.ai", "chat\\.z\\.ai", "claude\\.ai")
    $ok = 0
    foreach ($m in $matches) {
        try {
            $out = & node $restoreJs --port $Port --mode normal --match $m 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                Write-Host "CDP restored window for match=$m"
                $ok++
            } elseif ($out -match "NO_MATCHING_TAB") {
                # expected for lanes not open
            } else {
                Write-Host "CDP restore note ($m): $($out.Trim())"
            }
        } catch {
            Write-Warning "CDP restore failed for $m : $_"
        }
    }
    return $ok
}

Write-Host "Manual observation: fixing visible CDP lane Chrome windows..."
$win32Count = Restore-Lanes
if ($win32Count -eq 0) {
    Write-Host "Win32 found 0 titled windows — trying CDP Browser window restore fallback..."
    Restore-LanesViaCdp | Out-Null
}

if ($KeepVisible) {
    Write-Host "Keep-visible polling every $PollSeconds s (Ctrl+C to stop)..."
    while ($true) {
        Start-Sleep -Seconds $PollSeconds
        $c = Restore-Lanes
        if ($c -eq 0) { Restore-LanesViaCdp | Out-Null }
    }
}
Write-Host "Done. This script is intentionally blocked in autonomous paths unless -ManualObservation is set."