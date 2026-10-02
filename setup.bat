@echo off
cd /d "%~dp0"
py -3 bootstrap.py %*
if errorlevel 1 pause
exit /b %errorlevel%