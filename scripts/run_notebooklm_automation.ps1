# run_notebooklm_automation.ps1
param(
    [string]$PromptText,
    [string]$PromptFile,
    [int]$Port = 9224
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"

# Ensure output directory exists
$OutputDir = Join-Path $Repo "Nexus_News_Video_Outputs"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$DownloadsDir = "C:\Users\speci.000\Downloads"
Write-Host "Output Directory: $OutputDir"
Write-Host "Downloads Directory: $DownloadsDir"

# Record the list of existing mp4 files in Downloads
$existingMp4s = Get-ChildItem -Path $DownloadsDir -Filter "*.mp4" | Select-Object -ExpandProperty Name

$startTime = Get-Date
Write-Host "Starting NotebookLM automation at $startTime..."

# Build args
$nodeArgs = @(
    (Join-Path $Repo "scripts\notebooklm_video_automation.mjs"),
    "--port", $Port
)
if ($PromptFile) {
    $nodeArgs += @("--promptFile", $PromptFile)
} elseif ($PromptText) {
    $nodeArgs += @("--prompt", $PromptText)
}

# Run the Node script
& node @nodeArgs

Write-Host "Automation script completed. Waiting for new .mp4 file in Downloads..."

# Poll Downloads for new mp4 file
$newFile = $null
$deadline = (Get-Date).AddMinutes(10)
while ((Get-Date) -lt $deadline) {
    $currentMp4s = Get-ChildItem -Path $DownloadsDir -Filter "*.mp4"
    foreach ($file in $currentMp4s) {
        # Check if file is new or its write time is after start
        if ($existingMp4s -notcontains $file.Name -or $file.LastWriteTime -gt $startTime) {
            $newFile = $file
            break
        }
    }
    if ($newFile) {
        break
    }
    Start-Sleep -Seconds 5
}

if (-not $newFile) {
    Write-Error "Timeout: No new .mp4 file detected in Downloads after 10 minutes."
    exit 1
}

Write-Host "Detected new file download starting: $($newFile.Name)"
Write-Host "Waiting for download to complete (file lock release)..."

# Wait for file download to complete (size stops growing and file is not locked)
$lastSize = -1
$stableCount = 0
$maxWait = 120
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 2
    # Refresh file info
    $fileInfo = Get-Item $newFile.FullName
    $currentSize = $fileInfo.Length
    
    if ($currentSize -eq $lastSize -and $currentSize -gt 0) {
        $stableCount++
    } else {
        $stableCount = 0
        $lastSize = $currentSize
    }
    
    if ($stableCount -ge 3) {
        # Try to open file to ensure it's not locked by Chrome
        try {
            $stream = [System.IO.File]::Open($newFile.FullName, 'Open', 'Read', 'None')
            $stream.Close()
            break
        } catch {
            Write-Host "File is still locked/downloading..."
        }
    }
}

# Copy the file to the output directory
$destination = Join-Path $OutputDir $newFile.Name
Copy-Item -Path $newFile.FullName -Destination $destination -Force
Write-Host "File successfully copied to project drive: $destination"
Write-Host (ConvertTo-Json @{ status = "SUCCESS"; file = $newFile.Name; path = $destination } -Compress)
exit 0
