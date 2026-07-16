# codex_behavior_monitor.ps1
# NEXUS Forensic Probe — Codex Desktop Behavior Monitor v1.0
# SHA256 baseline: collect on first run below
# Usage: powershell -ExecutionPolicy Bypass -File codex_behavior_monitor.ps1 -IntervalSec 10 -DurationMin 60

param(
    [int]$IntervalSec = 10,
    [int]$DurationMin = 60
)

$ErrorActionPreference = "SilentlyContinue"
$OutDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Timestamp = Get-Date -Format "yyyyMMddTHHmmss"
$LogFile = Join-Path $OutDir "codex_probe_${Timestamp}.forensic_log"
$EventsLog = Join-Path $OutDir "codex_events_${Timestamp}.forensic_log"
$NetLog = Join-Path $OutDir "codex_net_${Timestamp}.forensic_log"

# Baseline self-hash
$SelfHash = (Get-FileHash $MyInvocation.MyCommand.Path -Algorithm SHA256).Hash
$Baseline = @"
=== NEXUS FORENSIC PROBE BASELINE ===
Script: $($MyInvocation.MyCommand.Path)
SHA256: $SelfHash
Started: $(Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
Interval: ${IntervalSec}s
Duration: ${DurationMin}m
Host: $env:COMPUTERNAME
User: $env:USERNAME
OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)
"@
$Baseline | Out-File -FilePath $LogFile -Encoding UTF8
$Baseline | Out-File -FilePath $EventsLog -Encoding UTF8
$Baseline | Out-File -FilePath $NetLog -Encoding UTF8

$EndTime = (Get-Date).AddMinutes($DurationMin)
$SampleId = 0
$CrashCount = 0
$StunCount = 0
$LastStunState = $true
$StunStart = $null

function Write-Log($File, $Msg) {
    $Line = "[$(Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")] $Msg"
    $Line | Out-File -FilePath $File -Encoding UTF8 -Append
    Write-Host $Line
}

function Get-ProcessSnapshot {
    param([string[]]$Names)
    Get-Process -Name $Names -ErrorAction SilentlyContinue | Select-Object Id, ProcessName,
        @{N='CPU_s';E={[math]::Round($_.CPU, 1)}},
        @{N='WS_MB';E={[math]::Round($_.WorkingSet64 / 1MB, 1)}},
        @{N='PM_MB';E={[math]::Round($_.PagedMemorySize64 / 1MB, 1)}},
        @{N='Threads';E={$_.Threads.Count}},
        @{N='Handles';E={$_.HandleCount}},
        @{N='Responding';E={$_.Responding}},
        @{N='StartTime';E={$_.StartTime.ToString("HH:mm:ss")}}
}

function Get-NetworkSnapshot {
    param([int[]]$Pids)
    Get-NetTCPConnection -OwningProcess $Pids -ErrorAction SilentlyContinue | Select-Object @{N='PID';E={$_.OwningProcess}},
        LocalAddress, LocalPort, RemoteAddress, RemotePort, State
}

Write-Log $LogFile "### Monitor started. Sampling every ${IntervalSec}s for ${DurationMin}m."

while ((Get-Date) -lt $EndTime) {
    $SampleId++
    $Now = Get-Date

    # 1. Process snapshot
    $procs = Get-ProcessSnapshot @("ChatGPT", "codex")
    if ($procs) {
        Write-Log $LogFile "--- Sample $SampleId ---"
        $procs | ForEach-Object {
            $c = if ($_.CPU_s) { $_.CPU_s } else { 0.0 }
            $w = if ($_.WS_MB) { $_.WS_MB } else { 0.0 }
            $p = if ($_.PM_MB) { $_.PM_MB } else { 0.0 }
            $t = if ($_.Threads) { $_.Threads } else { 0 }
            $resp = if ($_.Responding) { "OK" } else { "STUN" }
            Write-Log $LogFile ("PROC: PID=" + $_.Id + " " + $_.ProcessName + " CPU=" + $c + "s WS=" + $w + "MB PM=" + $p + "MB Thr=" + $t + " Resp=" + $resp)

            # Stun detection: track transitions from OK→STUN
            if ($_.Responding -eq $false) {
                if ($LastStunState -eq $true) {
                    $StunStart = $Now
                    $StunCount++
                    Write-Log $LogFile "STUN_START: PID=$($_.Id) $($_.ProcessName) stun#$StunCount"
                }
                $LastStunState = $false
            } else {
                if ($LastStunState -eq $false -and $StunStart) {
                    $dur = ($Now - $StunStart).TotalSeconds
                    Write-Log $LogFile "STUN_END: PID=$($_.Id) $($_.ProcessName) duration=${dur}s"
                }
                $LastStunState = $true
                $StunStart = $null
            }
        }
    } else {
        Write-Log $LogFile "WARN: No ChatGPT/codex process found"
    }

    # 2. Crash event check
    $newCrashes = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000; StartTime=$Now.AddSeconds(-$IntervalSec*2)} -MaxEvents 10 -ErrorAction SilentlyContinue `
        | Where-Object { $_.Message -match "ChatGPT\.exe|codex\.exe" }
    if ($newCrashes) {
        $crashDelta = ($newCrashes | Measure-Object).Count
        $CrashCount += $crashDelta
        $newCrashes | ForEach-Object {
            $ec = if ($_.Message -match 'Exception code: (0x[0-9a-fA-F]+)') { $matches[1] } else { "?" }
            Write-Log $EventsLog "CRASH: Time=$($_.TimeCreated.ToString('HH:mm:ss')) Exception=$ec PID=$($_.ProcessId)"
        }
    }

    # 3. Network snapshot (every 5 samples to reduce noise)
    if ($SampleId % 5 -eq 0) {
        $codexPid = (Get-Process -Name "codex" -ErrorAction SilentlyContinue | Select-Object -First 1).Id
        $chatPid = (Get-Process -Name "ChatGPT" -ErrorAction SilentlyContinue | Select-Object -First 1).Id
        $allPids = @($codexPid, $chatPid) | Where-Object { $_ -gt 0 }
        if ($allPids) {
            $net = Get-NetworkSnapshot -Pids $allPids
            if ($net) {
                Write-Log $NetLog "--- Net Sample $SampleId ---"
                $net | ForEach-Object {
                    Write-Log $NetLog "NET: PID=$($_.PID) $($_.LocalAddress):$($_.LocalPort) -> $($_.RemoteAddress):$($_.RemotePort) $($_.State)"
                }
            }
        }
    }

    # 4. Hash the current sample for forensic integrity
    $sampleHash = @{
        sample_id = $SampleId
        timestamp = $Now.ToString("yyyy-MM-ddTHH:mm:ssZ")
        proc_count = if ($procs) { ($procs | Measure-Object).Count } else { 0 }
        crash_total = $CrashCount
        stun_total = $StunCount
    }
    $sampleHashJson = $sampleHash | ConvertTo-Json -Compress
    $hashBytes = [System.Text.Encoding]::UTF8.GetBytes($sampleHashJson)
    $hashProvider = [System.Security.Cryptography.SHA256]::Create()
    $hashVal = [BitConverter]::ToString($hashProvider.ComputeHash($hashBytes)).Replace("-", "").ToLower()
    Write-Log $LogFile "SAMPLE_CHECKSUM: sample=$SampleId sha256=$hashVal"

    Start-Sleep -Seconds $IntervalSec
}

# Final summary
Write-Log $LogFile "=== MONITOR COMPLETE ==="
Write-Log $LogFile "Total samples: $SampleId"
Write-Log $LogFile "Total crashes detected: $CrashCount"
Write-Log $LogFile "Total stun events: $StunCount"
Write-Log $EventsLog "=== MONITOR COMPLETE: $SampleId samples, $CrashCount crashes, $StunCount stuns ==="
Write-Log $NetLog "=== MONITOR COMPLETE: $SampleId samples ==="
