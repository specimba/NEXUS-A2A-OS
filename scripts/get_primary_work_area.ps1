# Primary monitor working area (for lane Chrome geometry).
Add-Type -AssemblyName System.Windows.Forms
$wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
@{
    left   = $wa.Left
    top    = $wa.Top
    width  = $wa.Width
    height = $wa.Height
    right  = $wa.Right
    bottom = $wa.Bottom
} | ConvertTo-Json -Compress