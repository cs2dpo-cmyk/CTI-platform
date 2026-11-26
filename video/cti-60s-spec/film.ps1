# film.ps1 - build the CTI CISO dashboard 60 s film.
#
# Run this in a normal PowerShell window (not through an agent sandbox: a
# sandboxed shell on this machine cannot start a browser at all, see
# docs/video/notes.md).
#
# Steps:
#   1. capture   - real screenshots and measured boxes from the live site
#   2. build     - bundle the Remotion project (webpack, no esbuild)
#   3. stills    - the six hero frames + grid overlay + spec card for review
#   4. film      - only with -Film: render out/film.mp4 (H.264, crf 19)
#
# Examples:
#   .\film.ps1                 # capture + build + stills  (stage 1)
#   .\film.ps1 -SkipCapture    # reuse the captures already in public/captures
#   .\film.ps1 -SkipCapture -Film   # straight to the film

param(
  [switch]$SkipCapture,
  [switch]$NoStills,
  [switch]$Film
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Step($text) { Write-Host ""; Write-Host "=== $text " -NoNewline; Write-Host ("=" * [Math]::Max(0, 60 - $text.Length)) -ForegroundColor DarkGray }
function Fail($text) { Write-Host ""; Write-Host "FAILED: $text" -ForegroundColor Red; exit 1 }

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { Fail "node is not on PATH" }
if (-not (Test-Path "node_modules/remotion")) {
  Write-Host "installing dependencies..." -ForegroundColor Yellow
  npm ci --ignore-scripts --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { Fail "npm ci" }
}

if (-not $SkipCapture) {
  Step "1/4 capture the live page"
  node capture/capture.mjs
  if ($LASTEXITCODE -ne 0) { Fail "capture - nothing was overwritten, the previous captures are intact" }
} else {
  Write-Host "skipping capture (-SkipCapture)" -ForegroundColor DarkGray
}

Step "2/4 bundle"
node tools/build.cjs
if ($LASTEXITCODE -ne 0) { Fail "bundle" }

if (-not $NoStills) {
  Step "3/4 review stills"
  node tools/stills.cjs
  if ($LASTEXITCODE -ne 0) { Fail "stills" }
}

if ($Film) {
  Step "4/4 render the sample, then the film"
  node tools/render.cjs video Sample out/sample-640x360.mp4 24
  if ($LASTEXITCODE -ne 0) { Fail "sample render" }
  node tools/render.cjs video Master out/film.mp4 16
  if ($LASTEXITCODE -ne 0) { Fail "film render" }
}

Write-Host ""
Write-Host "done" -ForegroundColor Green
Write-Host "  stills : out/stills/"
if ($Film) { Write-Host "  sample : out/sample-640x360.mp4 (stage 2: rhythm, no texture)"; Write-Host "  film   : out/film.mp4" }
Write-Host "  captures: public/captures/  (values: public/data.json)"