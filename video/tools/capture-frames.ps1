<#
.SYNOPSIS
用本機 Edge 無頭模式，把指定秒數的畫面截成 PNG。
.NOTES
需要 Edge（Chromium）。無頭 Chromium 在 DSH 沙箱內無法啟動（mojo 具名管道被擋），
執行時需要較寬的權限。
.EXAMPLE
./capture-frames.ps1 -Times "1,3,5" -OutDir ../analysis/frames
#>
param(
  [string]$Times = "1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49,51,53,55,57,59",
  [string]$OutDir = "../analysis/frames",
  [string]$Edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$video = Split-Path -Parent $here
$out = if ([IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $video $OutDir }
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Path $out -Force | Out-Null

$url = "file:///" + ((Join-Path $video "index.html") -replace "\\", "/")
$profile = Join-Path $env:TEMP "dsh-edge-capture"
$n = 0
foreach ($t in ($Times -split ",")) {
  $t = $t.Trim()
  if (-not $t) { continue }
  $sec = [double]$t
  $p = Join-Path $out ("t{0:d2}.png" -f [int]$sec)
  $args2 = @(
    "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
    "--disable-crash-reporter", "--hide-scrollbars",
    "--user-data-dir=$profile", "--force-device-scale-factor=1",
    "--window-size=1920,1080", "--screenshot=$p",
    ($url + "?t=" + $sec + "&export=1")
  )
  & $Edge @args2 2>$null | Out-Null
  if (Test-Path $p) { $n++ } else { Write-Warning "failed t=$sec" }
}
Write-Host "captured $n frame(s) into $out"
