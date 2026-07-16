# Clean CDP Chrome: ONE visible window, no SilentBackground, no lane spam by default.
# Use when recover/start leaves frozen / off-screen / blank-tab mess.
param(
    [int]$Port = 9224,
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
    [switch]$OpenLanes,
    [switch]$RestoreLastSession,
    [switch]$AllowExtensions  # default OFF: extension offscreen pages + GPU black paint
)

$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"

Write-Host "=== start_cdp_clean_visible port=$Port ==="
Write-Host "Profile=$ProfileDir"
Write-Host "OpenLanes=$OpenLanes RestoreLastSession=$RestoreLastSession AllowExtensions=$AllowExtensions"

$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
)
$chrome = $null
foreach ($c in $chromeCandidates) {
    if ($c -and (Test-Path $c)) { $chrome = $c; break }
}
if (-not $chrome) {
    Write-Error "Google Chrome not found"
    exit 1
}
Write-Host "ChromeExe=$chrome"

# 1) Kill BrowserAI / port 9224 chrome only
Write-Host "Stopping BrowserAI profile Chrome..."
$killed = 0
Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {
    $procId = $_.Id
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        $cl = $proc.CommandLine
        if (-not $cl) { return }
        if ($cl -like "*BrowserAI*" -or $cl -like "*remote-debugging-port=$Port*") {
            Write-Host "  stop pid=$procId"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            $killed++
        }
    } catch {}
}
$listen = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
foreach ($ln in $listen) {
    $parts = @($ln.ToString() -split "\s+" | Where-Object { $_ -ne "" })
    $listenPid = 0
    [void][int]::TryParse($parts[-1], [ref]$listenPid)
    if ($listenPid -gt 0) {
        Write-Host "  stop listener pid=$listenPid"
        Stop-Process -Id $listenPid -Force -ErrorAction SilentlyContinue
        $killed++
    }
}
Write-Host "Killed=$killed"
Start-Sleep -Seconds 4

for ($i = 0; $i -lt 20; $i++) {
    $busy = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
    if (-not $busy) { Write-Host "Port $Port free"; break }
    Start-Sleep -Seconds 1
}

# 2) Reset window placement + clear GPU cache (black/glitch paint)
$reset = Join-Path $Repo "scripts\reset_lane_chrome_window_placement.ps1"
if (Test-Path $reset) {
    & $reset -ProfileDir $ProfileDir
}
foreach ($gpuDir in @("GPUCache", "GrShaderCache", "ShaderCache", "GraphiteDawnCache")) {
    $p = Join-Path $ProfileDir $gpuDir
    if (Test-Path $p) {
        Write-Host "Clearing $gpuDir..."
        Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
    }
}

# 3) Start ONE visible Chrome - NEVER -32000
# Hardware GPU by default. SwiftShader/TOPMOST thrash caused black+shutter for operator.
# Set NEXUS_CDP_SOFTWARE_GPU=1 only if pure-black returns without any force-window thrash.
$argList = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate,InterestCohorts,CalculateNativeWinOcclusion",
    "--hide-crash-restore-bubble",
    "--disable-backgrounding-occluded-windows",
    "--window-position=80,50",
    "--window-size=1280,900"
)
if ($env:NEXUS_CDP_SOFTWARE_GPU -eq "1") {
    Write-Warning "NEXUS_CDP_SOFTWARE_GPU=1 — software paint (may look soft; avoid force thrash)"
    $argList += @(
        "--disable-gpu",
        "--disable-gpu-compositing"
    )
}
if (-not $AllowExtensions) {
    $argList += @(
        "--disable-extensions",
        "--disable-component-extensions-with-background-pages"
    )
    Write-Host "Extensions OFF (pass -AllowExtensions to re-enable)"
}
if ($RestoreLastSession) {
    $argList += "--restore-last-session"
    Write-Warning "RestoreLastSession ON - may reintroduce blank tabs"
} else {
    $argList += "https://www.google.com/"
}

Write-Host "Starting VISIBLE Chrome..."
Write-Host ("Args=" + ($argList -join " "))
$started = Start-Process -FilePath $chrome -ArgumentList $argList -PassThru
if (-not $started) {
    Write-Error "Start-Process failed"
    exit 1
}
Write-Host "StartedChromePid=$($started.Id)"
Start-Sleep -Seconds 6

$up = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $ver = Invoke-RestMethod "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
        Write-Host "[ok] CDP up browser=$($ver.Browser)"
        $up = $true
        break
    } catch {
        Write-Host "  wait CDP $i"
        Start-Sleep -Seconds 1
    }
}
if (-not $up) {
    Write-Warning "CDP port $Port not up"
    exit 1
}

# 4) Force on-screen
$force = "C:\Users\speci.000\Downloads\cdp_agent_scratch\intern_cdp\_force_cdp_chrome_visible.ps1"
if (Test-Path $force) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $force -Port $Port
} else {
    $restore = Join-Path $Repo "scripts\restore_chrome_cdp_window.ps1"
    if (Test-Path $restore) {
        & $restore -Port $Port -SkipEnsure -ForceShow -Interactive
    }
}

# 5) Lanes OFF by default
if ($OpenLanes) {
    Write-Warning "Opening all lanes (heavy)"
    & (Join-Path $Repo "scripts\open_all_browser_lanes.ps1") -Port $Port -SkipEnsure
} else {
    Write-Host "Lanes NOT opened. Manually open Intern when needed."
}

try {
    $pages = @((Invoke-RestMethod "http://127.0.0.1:$Port/json/list" -TimeoutSec 4) | Where-Object { $_.type -eq "page" })
    Write-Host "PAGES=$($pages.Count)"
    foreach ($pg in $pages | Select-Object -First 12) {
        Write-Host ("  - " + $pg.title)
    }
} catch {
    Write-Host "list pages failed"
}

Write-Host "STATUS=CDP_CLEAN_VISIBLE port=$Port openLanes=$OpenLanes"
exit 0
