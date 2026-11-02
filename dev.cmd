@echo off
rem Double-click launcher for the CTI Risk Decision Platform.
rem Windows opens .ps1 files in an editor, so this shell runs dev.ps1 for you,
rem keeps the window open on exit, and forwards any arguments.

setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>nul

set "PS_EXE="

where pwsh >nul 2>nul
if not errorlevel 1 set "PS_EXE=pwsh"

if not defined PS_EXE (
    where powershell >nul 2>nul
    if not errorlevel 1 set "PS_EXE=powershell"
)

if not defined PS_EXE (
    echo.
    echo   [x] PowerShell was not found on this machine.
    echo.
    pause
    exit /b 1
)

"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" echo   dev.ps1 exited with code %EXITCODE%.
echo   This window can be closed now.
pause
exit /b %EXITCODE%
