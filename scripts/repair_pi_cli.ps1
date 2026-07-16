[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '0.75.3'
)

<##
.SYNOPSIS
Repairs the exact Pi Coding Agent package expected by the current pnpm shim.

.DESCRIPTION
This is deliberately a repair, not an uncontrolled upgrade: it reinstalls the
version encoded in the broken global shim and then proves `pi --version` works.
It never changes Pi models.json, auth.json, settings.json, or extensions.
Use -WhatIf to inspect the mutation before execution.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpm) {
    throw 'pnpm is required to repair Pi, but it is not available on PATH.'
}

$package = "@earendil-works/pi-coding-agent@$Version"
function Get-PiVersionProbe {
    $previousErrorAction = $ErrorActionPreference
    try {
        # A broken pnpm shim writes Node's module error to stderr. Capture it
        # as probe data rather than allowing PowerShell's native-command error
        # adapter to abort the repair before pnpm can restore the package.
        $ErrorActionPreference = 'Continue'
        $output = (& pi --version 2>&1 | Out-String).Trim()
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

$before = Get-PiVersionProbe
if ($before.ExitCode -eq 0) {
    [pscustomobject]@{
        repaired = $false
        healthy = $true
        package = $package
        version = ($before.Output -split "`r?`n" | Select-Object -First 1).ToString().Trim()
        reason = 'pi_cli_already_healthy'
    } | ConvertTo-Json -Compress
    exit 0
}

if (-not $PSCmdlet.ShouldProcess('pnpm global package store', "install $package")) {
    [pscustomobject]@{
        repaired = $false
        healthy = $false
        package = $package
        reason = 'whatif_or_declined'
    } | ConvertTo-Json -Compress
    exit 0
}

& $pnpm.Source add --global $package
if ($LASTEXITCODE -ne 0) {
    throw "pnpm failed while installing $package (exit $LASTEXITCODE)."
}

$after = Get-PiVersionProbe
if ($after.ExitCode -ne 0) {
    throw "Pi package installation completed but 'pi --version' still failed (exit $($after.ExitCode))."
}

[pscustomobject]@{
    repaired = $true
    healthy = $true
    package = $package
    version = ($after.Output -split "`r?`n" | Select-Object -First 1).ToString().Trim()
    reason = 'exact_shim_package_reinstalled'
} | ConvertTo-Json -Compress
