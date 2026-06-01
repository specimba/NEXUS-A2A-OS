param(
  [datetime]$Since = (Get-Date '2026-05-18T02:10:00')
)
$events = @(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WHEA-Logger'; StartTime=$Since} -ErrorAction SilentlyContinue)
if ($events.Count -eq 0) {
  Write-Output "No WHEA events since $Since"
  exit 0
}
$events | Group-Object Id | Sort-Object Name | Select-Object Name,Count | Format-Table -AutoSize
$events | Select-Object TimeCreated,Id,LevelDisplayName,Message | Format-List
