param(
    [string]$ProfileDir = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile",
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$wa = & "$Repo\scripts\get_primary_work_area.ps1" | ConvertFrom-Json
$py = "$Repo\.venv\Scripts\python.exe"
$script = "$Repo\nexus_os\nexusclaw\reset_chrome_lane_window_placement.py"
$extra = @()
if ($Interactive) { $extra += "--no-maximized" }
& $py $script --profile-dir $ProfileDir `
    --width 1280 --height 900 --left 80 --top 50 `
    --work-right $wa.right --work-bottom $wa.bottom @extra