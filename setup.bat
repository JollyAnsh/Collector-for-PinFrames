@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="-delete" if "%~2"=="" goto delete

set "UV_CACHE_DIR=%CD%\.uv-cache"
set "UV_PYTHON_INSTALL_DIR=%CD%\.uv-python"
set "PLAYWRIGHT_BROWSERS_PATH=%CD%\.playwright-browsers"

if not exist ".tools\uv.exe" (
    if not exist ".tools" mkdir ".tools"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; $env:UV_INSTALL_DIR = (Join-Path (Get-Location) '.tools'); irm https://astral.sh/uv/install.ps1 | iex; if (-not (Test-Path (Join-Path $env:UV_INSTALL_DIR 'uv.exe'))) { exit 1 }"
    if errorlevel 1 goto failed
)

".tools\uv.exe" run --python 3.12 --no-project bootstrap.py %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%

:failed
set "EXIT_CODE=%ERRORLEVEL%"
echo Failed to download or install uv. Check your internet connection and try again.
pause
exit /b %EXIT_CODE%

:delete
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; foreach ($p in @('.venv', '.tools', '.uv-cache', '.uv-python', '.playwright-browsers')) { if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Recurse -Force } }"
if errorlevel 1 goto delete_failed
echo Removed the collector's Python environment, uv runtime/cache, and Chromium.
echo The saved feed token and Pinterest login were preserved.
exit /b 0

:delete_failed
echo Failed to remove one or more collector dependency directories.
pause
exit /b 1