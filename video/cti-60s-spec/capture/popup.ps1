# popup.ps1 - capture the five native <select> popups from the real screen.
#
# A native select's popup belongs to the OS, so page.screenshot() cannot see it. The
# only way to get those pixels is to open the menu in a headed window and grab the
# screen.
#
# Coordinate rule: every position in openPositions.json is a CSS px inside the page's
# viewport, so a screen point is
#     clientOrigin + css * scale
# where clientOrigin is the client area's top-left ON SCREEN, measured with
# ClientToScreen. Assuming the window sits at (0,0) is what made the first two runs
# click the overview page instead of the assess tab.
#
#   node capture/popup-positions.mjs
#   powershell -ExecutionPolicy Bypass -File capture\popup.ps1

param(
  [string]$Base = "https://cti-risk-platform.onrender.com/",
  [double]$Scale = 1.0     # headed window runs with --force-device-scale-factor=1
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)

$posFile = "public/openPositions.json"
if (-not (Test-Path $posFile)) { throw "run: node capture/popup-positions.mjs first" }
$pos = Get-Content $posFile -Raw | ConvertFrom-Json
if (-not $pos.tab) { throw "no tab rect - re-run node capture/popup-positions.mjs" }

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
"@
[W]::SetProcessDPIAware() | Out-Null

function ClickAt([int]$x, [int]$y) {
  [W]::SetCursorPos($x, $y) | Out-Null
  Start-Sleep -Milliseconds 120
  [W]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
  [W]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
}

function Grab([string]$path, $rect) {
  $bmp = New-Object System.Drawing.Bitmap $rect.Width, $rect.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen((New-Object System.Drawing.Point $rect.X, $rect.Y), [System.Drawing.Point]::Empty, $rect.Size)
  $secure = (Resolve-Path "public/captures").Path + "\" + $path
  $bmp.Save($secure, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}

$EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
$profile = Join-Path $env:TEMP ("popup-profile-" + [guid]::NewGuid().ToString("N"))
$size = "{0},{1}" -f [int]$pos.viewport.W, [int]$pos.viewport.H

Write-Host "opening Edge (kiosk) ..." -ForegroundColor Cyan
$launchedAt = (Get-Date).AddSeconds(-2)
# --guest, no sync, no translate bubble: the first two runs failed because Edge's
# "we are syncing your browsing data" dialog opened exactly on top of the tab strip,
# so every click landed on the dialog instead of the page.
# --kiosk, not --window-size: a windowed Edge landed on a 1295x986 client, so the page
# laid out at ~1036 css px and every measured position was for the wrong layout. Kiosk
# is true fullscreen: client = screen = 1920x1080 device = 1536x864 css at 125%.
$edge = Start-Process -FilePath $EDGE -PassThru -ArgumentList @(
  "--kiosk", "--force-device-scale-factor=1",
  "--guest", "--disable-sync",
  "--disable-features=Translate,TranslateUI,msEdgeSync,EdgeSyncPromo",
  "--no-first-run", "--no-default-browser-check", "--force-color-profile=srgb",
  $Base
)
Start-Sleep -Seconds 12

# the client origin is the whole ballgame
# Start-Process hands back the launcher, which exits immediately, so MainWindowHandle
# is null. Find the window by its page title instead ("... CISO Dashboard").
# Match on the process start time, not just the title: a leftover window from an
# earlier run has the same title and the same look, and the script happily measured
# the stale one and clicked into it.
$hwnd = [IntPtr]::Zero
for ($i = 0; $i -lt 40 -and $hwnd -eq [IntPtr]::Zero; $i++) {
  Start-Sleep -Milliseconds 500
  # no StartTime filter: reading StartTime throws on some processes and silently
  # emptied the candidate list. Title match only, preferring the one that mentions CTI.
  $all = @(Get-Process msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
  $cand = $all | Where-Object { $_.MainWindowTitle -like "*CTI*" } | Select-Object -First 1
  if (-not $cand) { $cand = $all | Where-Object { $_.MainWindowTitle } | Select-Object -First 1 }
  if ($cand) { $hwnd = [IntPtr]$cand.MainWindowHandle; $foundTitle = $cand.MainWindowTitle }
}
if ($hwnd -eq [IntPtr]::Zero) { throw "could not find any Edge window" }
Write-Host ("window: " + $foundTitle) -ForegroundColor DarkGray
[W]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 600

$pt = New-Object W+POINT
[W]::ClientToScreen($hwnd, [ref]$pt) | Out-Null
$cr = New-Object W+RECT
[W]::GetClientRect($hwnd, [ref]$cr) | Out-Null
Write-Host ("client origin on screen: {0},{1}   client size: {2}x{3}" -f $pt.X, $pt.Y, $cr.R, $cr.B) -ForegroundColor DarkGray
$expectedW = [int]($pos.viewport.W * $Scale)
$expectedH = [int]($pos.viewport.H * $Scale)
if ([Math]::Abs($cr.R - $expectedW) -gt 8 -or [Math]::Abs($cr.B - $expectedH) -gt 8) {
  Write-Host ("WARNING: client is {0}x{1}, positions were measured for {2}x{3} - the page layout will not match" -f $cr.R, $cr.B, $expectedW, $expectedH) -ForegroundColor Yellow
}
$ox = $pt.X; $oy = $pt.Y

# clear any bubble that still made it through, then switch to the assess tab
[W]::keybd_event(0x1B, 0, 0, [IntPtr]::Zero)
[W]::keybd_event(0x1B, 0, 2, [IntPtr]::Zero)
Start-Sleep -Milliseconds 400
$tx = $ox + [int](($pos.tab.x + $pos.tab.w / 2) * $Scale)
$ty = $oy + [int](($pos.tab.y + $pos.tab.h / 2) * $Scale)
ClickAt $tx $ty
Start-Sleep -Milliseconds 1500
Grab "assess-open-00-check.png" (New-Object System.Drawing.Rectangle $ox, $oy, $cr.R, $cr.B)

$order = @("assetType", "threatSource", "category", "exposure", "exploitStatus")
$i = 0
foreach ($key in $order) {
  $i++
  $s = $pos.selects.$key
  $cx = $ox + [int](($s.x + $s.w / 2) * $Scale)
  $cy = $oy + [int](($s.y + $s.h / 2) * $Scale)
  ClickAt $cx $cy
  Start-Sleep -Milliseconds 500

  $padTop = 8
  $x0 = $ox + [int](($s.x - 16) * $Scale)
  $y0 = $oy + [int](($s.y - $padTop) * $Scale)
  $cw = [int](($s.w + 32) * $Scale)
  $ch = [int](300 * $Scale)
  Grab ("assess-open-" + $i.ToString("00") + ".png") (New-Object System.Drawing.Rectangle $x0, $y0, $cw, $ch)

  Write-Host ("  {0} -> assess-open-{1}.png  {2}x{3}" -f $key, $i.ToString("00"), $cw, $ch) -ForegroundColor Green
  [W]::keybd_event(0x1B, 0, 0, [IntPtr]::Zero)
  [W]::keybd_event(0x1B, 0, 2, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 300
}

Stop-Process -Id $edge.Id -Force -ErrorAction SilentlyContinue
Remove-Item $profile -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "done" -ForegroundColor Cyan
