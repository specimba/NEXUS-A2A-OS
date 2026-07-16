param(
    [int]$DurationMin = 120,
    [int]$IntervalSec = 10
)

$ErrorActionPreference = "SilentlyContinue"
$OutDir = "C:\Users\speci.000\Documents\NEXUS\tools\forensics"
$Timestamp = Get-Date -Format "yyyyMMddTHHmmss"
$LogFile = Join-Path $OutDir "codex_probe_${Timestamp}.forensic_log"
$EventsLog = Join-Path $OutDir "codex_events_${Timestamp}.forensic_log"

$Baseline = "=== NEXUS FORENSIC PROBE v2 ==="
$Baseline += "`nStarted: " + (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$Baseline += "`nHost: " + $env:COMPUTERNAME
$Baseline += "`nUser: " + $env:USERNAME
$Baseline | Out-File -FilePath $LogFile -Encoding UTF8
$Baseline | Out-File -FilePath $EventsLog -Encoding UTF8

$EndTime = (Get-Date).AddMinutes($DurationMin)
$SampleId = 0
$CrashCount = 0
$StunCount = 0
$LastStunState = @{}
$StunStart = @{}

while ((Get-Date) -lt $EndTime) {
    $SampleId++
    $procs = Get-Process -Name "ChatGPT","codex" -ErrorAction SilentlyContinue
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"

    if ($procs) {
        foreach ($p in $procs) {
            $c = if ($p.CPU) { [math]::Round($p.CPU, 1) } else { 0.0 }
            $w = if ($p.WorkingSet64) { [math]::Round($p.WorkingSet64 / 1MB, 1) } else { 0.0 }
            $pm = if ($p.PagedMemorySize64) { [math]::Round($p.PagedMemorySize64 / 1MB, 1) } else { 0.0 }
            $t = if ($p.Threads) { $p.Threads.Count } else { 0 }
            $resp = if ($p.Responding) { "OK" } else { "STUN" }
            $h = if ($p.HandleCount) { $p.HandleCount } else { 0 }

            $line = "[$timestamp] PID=" + $p.Id + " " + $p.ProcessName + " CPU=" + $c + "s WS=" + $w + "MB PM=" + $pm + "MB Thr=" + $t + " Hnd=" + $h + " Resp=" + $resp
            $line | Out-File -FilePath $LogFile -Append -Encoding UTF8

            # Stun detection
            $pidStr = [string]$p.Id
            if ($p.Responding -eq $false) {
                if (-not $LastStunState.ContainsKey($pidStr) -or $LastStunState[$pidStr] -eq $true) {
                    $StunStart[$pidStr] = Get-Date
                    $StunCount++
                    $sline = "[$timestamp] STUN_START: PID=" + $p.Id + " stun#" + $StunCount
                    $sline | Out-File -FilePath $LogFile -Append -Encoding UTF8
                }
                $LastStunState[$pidStr] = $false
            } else {
                if ($LastStunState.ContainsKey($pidStr) -and $LastStunState[$pidStr] -eq $false -and $StunStart.ContainsKey($pidStr)) {
                    $dur = [math]::Round(((Get-Date) - $StunStart[$pidStr]).TotalSeconds, 1)
                    $sline = "[$timestamp] STUN_END: PID=" + $p.Id + " dur=" + $dur + "s"
                    $sline | Out-File -FilePath $LogFile -Append -Encoding UTF8
                }
                $LastStunState[$pidStr] = $true
            }
        }
    } else {
        $line = "[$timestamp] WARN: No ChatGPT/codex process found"
        $line | Out-File -FilePath $LogFile -Append -Encoding UTF8
    }

    # Check for new crashes (check last 15 seconds)
    $crashes = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000} -MaxEvents 10 -ErrorAction SilentlyContinue
    if ($crashes) {
        $crashes | ForEach-Object {
            if ($_.TimeCreated -gt (Get-Date).AddSeconds(-$IntervalSec * 2) -and $_.Message -match "ChatGPT") {
                $ec = "?"
                if ($_.Message -match 'Exception code: (0x[0-9a-fA-F]+)') {
                    $ec = $matches[1]
                }
                $ct = $_.TimeCreated.ToString("HH:mm:ss")
                $cline = "[$timestamp] CRASH: time=" + $ct + " exc=" + $ec + " count=" + ($CrashCount+1)
                $cline | Out-File -FilePath $EventsLog -Append -Encoding UTF8
                $CrashCount++
            }
        }
    }

    # Summary every 30 samples
    if ($SampleId % 30 -eq 0) {
        $sline = "[$timestamp] STATUS: samples=" + $SampleId + " crashes=" + $CrashCount + " stuns=" + $StunCount
        $sline | Out-File -FilePath $LogFile -Append -Encoding UTF8
    }

    Start-Sleep -Seconds $IntervalSec
}

$final = "[$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffZ')] MONITOR_DONE: samples=" + $SampleId + " crashes=" + $CrashCount + " stuns=" + $StunCount
$final | Out-File -FilePath $LogFile -Append -Encoding UTF8
