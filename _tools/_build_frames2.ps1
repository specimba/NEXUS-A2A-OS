Add-Type -AssemblyName System.Drawing
$packDir = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\assets\video\media-pack"
New-Item -ItemType Directory -Force -Path $packDir -ErrorAction SilentlyContinue | Out-Null
$shots = Get-Content (Join-Path $packDir "shots.json") -Raw | ConvertFrom-Json
foreach ($s in $shots) {
  $bmp = New-Object System.Drawing.Bitmap 1280,720
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::Black)
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $fontTitle = New-Object System.Drawing.Font("Arial", [float]$s.size, [System.Drawing.FontStyle]::Bold)
  $brush = New-Object System.Drawing.SolidColor ([System.Drawing.Color]::FromName($s.color))
  $fmt = New-Object System.Drawing.StringFormat
  $fmt.Alignment = [System.Drawing.StringAlignment]::Center
  $fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
  $rect = New-Object System.Drawing.RectangleF 0,250, 1280, 200
  $g.DrawString($s.title, $fontTitle, $brush, $rect, $fmt)
  if ($s.subtitle -and $s.subtitle.Length -gt 0) {
    $fontSub = New-Object System.Drawing.Font("Arial", 24, [System.Drawing.FontStyle]::Regular)
    $rect2 = New-Object System.Drawing.RectangleF 0,400, 1280, 100
    $g.DrawString($s.subtitle, $fontSub, $brush, $rect2, $fmt)
  }
  $fontWm = New-Object System.Drawing.Font("Arial", 14, [System.Drawing.FontStyle]::Regular)
  $brushWm = New-Object System.Drawing.SolidColor ([System.Drawing.Color]::FromName("gray"))
  $g.DrawString("NEXUS Sentinel / UiPath AgentHack 2026", $fontWm, $brushWm, 20, 680)
  $safeName = $s.title -replace " ", "-" -replace "[^a-zA-Z0-9-]", ""
  $safeName = $safeName.Substring(0, [Math]::Min(20, $safeName.Length))
  $path = Join-Path $packDir ("frame-0" + $s.idx + "-" + $safeName + ".png")
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose()
  $bmp.Dispose()
  Write-Output ("SAVED: " + (Get-Item $path).Length + " bytes - " + (Split-Path $path -Leaf))
}
Write-Output ""
Write-Output "=== ALL FRAMES ==="
Get-ChildItem $packDir -Filter "*.png" | Select-Object Name, Length | Format-Table -AutoSize