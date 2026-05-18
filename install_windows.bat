@echo off
setlocal
set "PROJECT_DIR=%~dp0"
powershell -ExecutionPolicy Bypass -File "%PROJECT_DIR%install_windows.ps1"
pause
