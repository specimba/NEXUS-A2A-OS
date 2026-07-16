# a800_lightweight_monitor.ps1
param(
    [int]$MaxStaleMinutes = 15,
    [string]$GhRepo = "specimba/NEXUS_discovery_GPU",
    [string]$HeartbeatPath = "reports/session4/a800/HEARTBEAT.json",
    [string]$LocalFallback = "C:\Users\speci.000\Documents\NEXUS\scratch\a800_heartbeat.json",
    [string]$LogPath = "C:\Users\speci.000\Downloads\NEXUSlogs\a800_monitor_scheduled.log",
    [string]$StatePath = "C:\Users\speci.000\Documents\NEXUS\scratch\a800_monitor_state.json"
)

$ErrorActionPreference = "SilentlyContinue"

# Ensure log directory exists
$logDir = [System.IO.Path]::GetDirectoryName($LogPath)
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

function Get-HeartbeatFromGH {
    try {
        $json = gh api "repos/$GhRepo/contents/$HeartbeatPath" --jq ".content" 2>$null
        if ($json) {
            $decoded = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($json))
            return $decoded | ConvertFrom-Json
        }
        return @{ Error = "no_content" }
    }
    catch {
        return @{ Error = $_.Exception.Message }
    }
}

function Get-HeartbeatFromLocal {
    try {
        if (Test-Path $LocalFallback) {
            $content = Get-Content $LocalFallback -Raw -ErrorAction Stop
            return $content | ConvertFrom-Json
        }
        return @{ Error = "no_local_file" }
    }
    catch {
        return @{ Error = $_.Exception.Message }
    }
}

# Load previous state
$state = @{ lastTick = -1; lastTickTime = (Get-Date).ToString("o"); stallCount = 0 }
if (Test-Path $StatePath) {
    try {
        $loaded = Get-Content $StatePath -Raw | ConvertFrom-Json
        if ($loaded) {
            if ($loaded.lastTick -ne $null) { $state.lastTick = [int]$loaded.lastTick }
            if ($loaded.lastTickTime -ne $null) { $state.lastTickTime = $loaded.lastTickTime }
            if ($loaded.stallCount -ne $null) { $state.stallCount = [int]$loaded.stallCount }
        }
    } catch {}
}

# Fetch the current heartbeat
$hb = Get-HeartbeatFromGH
if ($hb.Error) {
    $hb = Get-HeartbeatFromLocal
}

if ($hb.Error) {
    Write-Log "Heartbeat unavailable: $($hb.Error)" "ERROR"
    exit 1
}

$tick = [int]$hb.tick
$stamp = $hb.stamp
$mode = $hb.mode
$projectPct = [int]$hb.project_pct

# Parse heartbeat time
$hbTime = [datetime]::Parse($stamp)
$age = (Get-Date) - $hbTime

# Evaluate advancement
if ($tick -gt $state.lastTick) {
    $delta = $tick - $state.lastTick
    $lastTime = [datetime]::Parse($state.lastTickTime)
    $elapsed = ((Get-Date) - $lastTime).TotalMinutes
    $rate = if ($elapsed -gt 0) { [math]::Round($delta / $elapsed * 60, 1) } else { 0 }
    
    Write-Log "tick=$tick (+$delta) age=$([int]$age.TotalMinutes)min rate=${rate}t/h mode=$mode project=$projectPct%" "OK"
    
    $state.lastTick = $tick
    $state.lastTickTime = (Get-Date).ToString("o")
    $state.stallCount = 0
}
elseif ($age.TotalMinutes -gt $MaxStaleMinutes) {
    $state.stallCount++
    Write-Log "STALL #$($state.stallCount): tick=$tick unchanged, heartbeat age=$([int]$age.TotalMinutes)min > ${MaxStaleMinutes}min" "WARN"
}
else {
    Write-Log "tick=$tick (no change) age=$([int]$age.TotalMinutes)min" "IDLE"
}

# Enforce A800 capacity rules (GND-001 / A800-HR-001)
if ($projectPct -ge 90) {
    Write-Log "CRITICAL CAPACITY ALERT: Project Disk at $projectPct%! Hub downloads halted." "ALERT"
}

# Save updated state
$state | ConvertTo-Json | Set-Content $StatePath -Force
exit 0
