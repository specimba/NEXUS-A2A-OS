Add-Type -AssemblyName System.Drawing
$packDir = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\assets\video\media-pack"
New-Item -ItemType Directory -Force -Path $packDir -ErrorAction SilentlyContinue | Out-Null
$shotTimes = @({idx=1, dur=3, title="NEXUS SENTINEL", subtitle="", color="white", size=88, bold=$true}, {idx=2, dur=4, title="Production AI recovery is ad-hoc.", subtitle="We built a typed contract.", color="white", size=42, bold=$false}, {idx=3, dur=8, title="5 STAGES", subtitle="Evaluate > Route > Approve > Verify > Re-evaluate", color="white", size=36, bold=$true}, {idx=4, dur=7, title="LIVE VERDICT CHAIN", subtitle="HOLD > ALLOW > FAILED > PASSED", color="yellow", size=48, bold=$true}, {idx=5, dur=3, title="Audit-chain integrity: True", subtitle="Runtime: 2.64 seconds", color="lime", size=40, bold=$true}, {idx=6, dur=3, title="github.com/specimba/NEXUS_UiPathAgentHack", subtitle="", color="white", size=32, bold=$false}, {idx=7, dur=2, title="UiPath AgentHack 2026", subtitle="", color="white", size=36, bold=$false})
foreach ($s in $shotTimes) {
  $bmp = New-Object System.Drawing.Bitmap 1280,720
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::Black)
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  # Center text vertically
  $y = 280
  $fontTitle = New-Object System.Drawing.Font("Arial", $s.size, [System.Drawing.FontStyle]::Bold)
  $brush = New-Object System.Drawing.SolidColor ([System.Drawing.Color]::FromName($s.color))
  $fmt = New-Object System.Drawing.StringFormat
  $fmt.Alignment = [System.Drawing.StringAlignment]::Center
  $fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
  $rect = New-Object System.Drawing.RectangleF 0,$y, 1280, 200
  $g.DrawString($s.title, $fontTitle, $brush, $rect, $fmt)
  if ($s.subtitle) {
    $fontSub = New-Object System.Drawing.Font("Arial", 24, [System.Drawing.FontStyle]::Regular)
    $rect2 = New-Object System.Drawing.RectangleF 0,($y + 130), 1280, 100
    $g.DrawString($s.subtitle, $fontSub, $brush, $rect2, $fmt)
  }
  # Watermark
  $fontWm = New-Object System.Drawing.Font("Arial", 14, [System.Drawing.FontStyle]::Regular)
  $brushWm = New-Object System.Drawing.SolidColor ([System.Drawing.Color]::FromName("gray"))
  $g.DrawString("NEXUS Sentinel / UiPath AgentHack 2026", $fontWm, $brushWm, 20, 680)
  $path = Join-Path $packDir ("frame-0" + $s.idx + "-" + ($s.title -replace " ", "-").Substring(0, [Math]::Min(20, $s.title.Length)) + ".png")
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose()
  $bmp.Dispose()
  Write-Output ("SAVED: " + $path + " (" + (Get-Item $path).Length + " bytes)")
}
Write-Output ""
Write-Output "=== ALL FRAMES ==="
Get-ChildItem $packDir | Select-Object Name, Length | Format-Table -AutoSize