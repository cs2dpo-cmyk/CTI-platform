#Requires -Version 5.1
<#
.SYNOPSIS
    One-click dev launcher for the CTI Risk Decision Platform.

.DESCRIPTION
    Finds a usable Python (project .venv, then the shared dependency folder next
    to the project, then the system interpreter), checks the runtime packages,
    picks a free port, opens the dashboard in the default browser and finally
    runs uvicorn in this console so closing the window stops the server.

.PARAMETER Port
    First port to try. Default 8123. If it is taken the next 9 ports are probed.

.PARAMETER Reload
    Start uvicorn with --reload (auto-restart on file changes).

.PARAMETER NoBrowser
    Do not open the browser automatically.

.PARAMETER Install
    Install requirements.txt without asking when the packages are missing.

.EXAMPLE
    .\dev.ps1
    .\dev.ps1 -Port 9000 -Reload
#>
[CmdletBinding()]
param(
    [int]$Port = 8123,
    [switch]$Reload,
    [switch]$NoBrowser,
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

try { $Host.UI.RawUI.WindowTitle = 'CTI Risk Platform - dev server' } catch { }

function Write-Info { param([string]$Message) Write-Host ('  ' + $Message) -ForegroundColor DarkGray }
function Write-Warn { param([string]$Message) Write-Host ('  ! ' + $Message) -ForegroundColor Yellow }
function Stop-With {
    param([string]$Message)
    Write-Host ''
    Write-Host ('  [x] ' + $Message) -ForegroundColor Red
    Write-Host ''
    exit 1
}

Write-Host ''
Write-Host '  ============================================================' -ForegroundColor DarkCyan
Write-Host '   CTI Risk Decision Platform  -  local dev server' -ForegroundColor Cyan
Write-Host '  ============================================================' -ForegroundColor DarkCyan
Write-Host ''

# --------------------------------------------------------------------------
# 1. Locate Python and the dependency folder
# --------------------------------------------------------------------------
$venvPython = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$sharedDeps = Join-Path (Split-Path -Parent $ProjectDir) '.pylibs'
$python = $null
$depsDir = $null

if (Test-Path $venvPython) {
    $python = $venvPython
    Write-Info 'python : .venv (project virtualenv)'
}
else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cmd) { $cmd = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if (-not $cmd) {
        Stop-With 'Python 3.10+ not found. Install it from https://www.python.org/downloads/ and enable "Add python.exe to PATH".'
    }
    $python = $cmd.Source
    if (Test-Path $sharedDeps) {
        $depsDir = (Resolve-Path $sharedDeps).Path
        Write-Info ('deps   : ' + $depsDir)
    }
    Write-Info ('python : ' + $python)
}

$pythonPathParts = @()
if ($depsDir) { $pythonPathParts += $depsDir }
$pythonPathParts += $ProjectDir
$env:PYTHONPATH = ($pythonPathParts -join ';')
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'

# --------------------------------------------------------------------------
# 2. Check / install the runtime packages
# --------------------------------------------------------------------------
function Test-Dependencies {
    & $python -c 'import fastapi, uvicorn, sqlalchemy, pydantic' 2>$null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Dependencies)) {
    Write-Warn 'runtime packages missing (fastapi / uvicorn / sqlalchemy / pydantic)'
    if (-not $Install) {
        $answer = Read-Host '  Install them into this Python now? [Y/n]'
        if ($answer -and $answer.Trim().ToLower().StartsWith('n')) {
            Stop-With 'Aborted. Manual install: pip install -r requirements.txt'
        }
    }
    Write-Info 'running: pip install -r requirements.txt'
    & $python -m pip install -r (Join-Path $ProjectDir 'requirements.txt')
    if (-not (Test-Dependencies)) {
        Stop-With 'Install failed. Try: python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt'
    }
    Write-Info 'packages installed'
}

# --------------------------------------------------------------------------
# 3. Pick a free port (or reuse an instance that is already running)
# --------------------------------------------------------------------------
function Test-PortFree {
    param([int]$Candidate)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $Candidate)
        $client.Close()
        return $false
    }
    catch {
        return $true
    }
}

function Get-RunningInstance {
    param([int]$Candidate)
    try {
        return (Invoke-RestMethod -Uri ("http://127.0.0.1:$Candidate/api/v1/health") -TimeoutSec 2)
    }
    catch {
        return $null
    }
}

$selectedPort = $null
foreach ($candidate in ($Port..($Port + 9))) {
    if (Test-PortFree -Candidate $candidate) {
        $selectedPort = $candidate
        break
    }
    $running = Get-RunningInstance -Candidate $candidate
    if ($running -and $running.status -eq 'ok') {
        Write-Host ("  i platform already running on port $candidate (" + $running.threats + ' threats)') -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process ("http://127.0.0.1:$candidate/") }
        Write-Host '  i reusing that instance - close its window to stop it.' -ForegroundColor DarkGray
        Write-Host ''
        exit 0
    }
}

if (-not $selectedPort) {
    Stop-With ("ports $Port-" + ($Port + 9) + ' are all busy.')
}

$url = "http://127.0.0.1:$selectedPort/"
$docsUrl = "http://127.0.0.1:$selectedPort/api/docs"

# --------------------------------------------------------------------------
# 4. Open the browser once the server answers (hidden helper process)
# --------------------------------------------------------------------------
if (-not $NoBrowser) {
    $shellExe = (Get-Command pwsh -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($shellExe) { $shellExe = $shellExe.Source } else { $shellExe = (Get-Process -Id $PID).Path }

    $probe = "for (`$i = 0; `$i -lt 60; `$i++) { try { Invoke-WebRequest -Uri '$($url)api/v1/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; Start-Process '$url'; break } catch { Start-Sleep -Milliseconds 500 } }"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($probe))
    try {
        Start-Process -FilePath $shellExe -ArgumentList @('-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden', '-EncodedCommand', $encoded) -WindowStyle Hidden | Out-Null
    }
    catch {
        Write-Warn 'could not launch the browser helper; open the URL manually.'
    }
}

# --------------------------------------------------------------------------
# 5. Run the server
# --------------------------------------------------------------------------
Write-Host ''
Write-Host ('  url    : ' + $url) -ForegroundColor Green
Write-Host ('  docs   : ' + $docsUrl)
Write-Host ('  data   : ' + (Join-Path $ProjectDir 'data\cti.db'))
Write-Host  '  stop   : Ctrl+C, or close this window'
Write-Host ''
Write-Host '  ------------------------------------------------------------' -ForegroundColor DarkCyan
Write-Host ''

$uvicornArgs = @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', "$selectedPort")
if ($Reload) { $uvicornArgs += '--reload' }

$exitCode = 0
try {
    & $python @uvicornArgs
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host ''
    Write-Host ('  [x] ' + $_.Exception.Message) -ForegroundColor Red
    $exitCode = 1
}

Write-Host ''
if ($exitCode -ne 0) {
    Write-Host ("  server exited with code $exitCode") -ForegroundColor Yellow
}
else {
    Write-Host '  server stopped.' -ForegroundColor DarkGray
}
Write-Host ''
