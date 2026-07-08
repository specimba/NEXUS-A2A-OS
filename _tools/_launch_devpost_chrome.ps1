$port = 9226
$profile = "C:\Users\speci.000\AppData\Local\Temp\sai-devpost-profile"
if (Test-Path $profile) { Remove-Item -Recurse -Force $profile }
New-Item -ItemType Directory -Force -Path $profile | Out-Null
$chrome = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -ErrorAction SilentlyContinue)."(default)"
if (-not $chrome) { $chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe" }
if (-not (Test-Path $chrome)) { $chrome = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" }
Write-Output ("Chrome path: " + $chrome)
Write-Output ("Profile dir: " + $profile)
Write-Output ("CDP port:    " + $port)
Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
$args = @(
  "--remote-debugging-port=" + $port,
  "--remote-allow-origins=*",
  "--user-data-dir=" + $profile,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-popup-blocking",
  "--disable-notifications",
  "--window-size=1280,900",
  "https://devpost.com/submit-to/29624-uipath-agenthack/manage/submissions/1067995-nexus_uipathagenthack/project_details/edit"
)
$proc = Start-Process -FilePath $chrome -ArgumentList $args -PassThru
Write-Output ("Started Chrome PID: " + $proc.Id)
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  try { $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/version" -TimeoutSec 2; if ($r) { $ready = $true; break } } catch { }
}
if ($ready) {
  $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/version"
  Write-Output ("CDP UP. Browser: " + $r.Browser)
} else {
  Write-Output "CDP did not come up in 10s"
}