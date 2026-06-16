<#
.SYNOPSIS
    Terminal Truth Packet — Pre/post action safety snapshot.
.DESCRIPTION
    Captures git status, branch, and working directory before
    and after an action. Use with DoppelGround lane discipline.
.PARAMETER Phase
    "pre" or "post" to indicate before/after action.
.EXAMPLE
    .\scripts\terminal_truth.ps1 -Phase pre
    # Run your action
    .\scripts\terminal_truth.ps1 -Phase post
#>

param(
    [Parameter(Mandatory)][ValidateSet("pre","post")][string]$Phase
)

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
$logFile = "$PSScriptRoot\..\terminal_truth_$(Get-Date -Format 'yyyyMMdd').log"

if ($Phase -eq "pre") {
    "=== [$timestamp] PRE-ACTION ===" | Add-Content $logFile
} else {
    "=== [$timestamp] POST-ACTION ===" | Add-Content $logFile
}

$status = git status --short 2>$null
$branch = git branch --show-current 2>$null
$cwd = Get-Location

"Branch: $branch" | Add-Content $logFile
"CWD: $cwd" | Add-Content $logFile
"Status:" | Add-Content $logFile
$status | Add-Content $logFile

if ($Phase -eq "post") {
    $diff = git diff --name-status 2>$null
    "Diff:" | Add-Content $logFile
    $diff | Add-Content $logFile
}

"" | Add-Content $logFile
Write-Host "[terminal_truth] $Phase snapshot written to $logFile"
