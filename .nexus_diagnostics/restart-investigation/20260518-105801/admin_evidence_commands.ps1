# Run from Administrator PowerShell. Report-only: no ownership changes, no driver changes, no firmware changes.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$admin = Join-Path $root 'admin-evidence-output'
New-Item -ItemType Directory -Force -Path $admin | Out-Null

Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | Export-Csv -NoTypeInformation -Path (Join-Path $admin 'bios-cim.csv')
Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,SystemType,TotalPhysicalMemory | Export-Csv -NoTypeInformation -Path (Join-Path $admin 'computer-system-cim.csv')
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,LastBootUpTime | Export-Csv -NoTypeInformation -Path (Join-Path $admin 'operating-system-cim.csv')
Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceName -match 'NVIDIA|GeForce|Intel.*Dynamic|Management Engine|Thermal|DTT' -or $_.DeviceID -match 'VEN_10DE|DEV_2860' } | Select-Object DeviceName,Manufacturer,DriverVersion,DriverDate,DeviceID | Export-Csv -NoTypeInformation -Path (Join-Path $admin 'pnp-signed-drivers.csv')
Get-CimInstance -Namespace root\cimv2 -ClassName Win32_ReliabilityRecords | Where-Object { $_.TimeGenerated -ge ((Get-Date).AddDays(-14)) } | Select-Object TimeGenerated,SourceName,EventIdentifier,ProductName,Message | Export-Csv -NoTypeInformation -Path (Join-Path $admin 'reliability-records-14d.csv')

$cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'
$sym = Join-Path $admin 'symbols'
New-Item -ItemType Directory -Force -Path $sym | Out-Null
Get-ChildItem C:\Windows\Minidump\*.dmp | Sort-Object LastWriteTime -Descending | ForEach-Object {
  $out = Join-Path $admin (($_.BaseName) + '-analyze-v.txt')
  & $cdb -y "srv*$sym*https://msdl.microsoft.com/download/symbols" -z $_.FullName -c "!analyze -v; q" *> $out
}

Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' | Format-List | Out-String | Set-Content -Path (Join-Path $admin 'crashcontrol-registry.txt')
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' | Select-Object PagingFiles,ExistingPageFiles,TempPageFile,AutomaticManagedPagefile | Format-List | Out-String | Set-Content -Path (Join-Path $admin 'pagefile-registry.txt')
'Admin evidence collection complete. Review files before making any system changes.' | Set-Content -Path (Join-Path $admin 'README.txt')
