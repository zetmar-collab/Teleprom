@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONW=%PROJECT_DIR%.venv\Scripts\pythonw.exe"
set "PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"

if exist "%PYTHONW%" (
  start "" "%PYTHONW%" "%PROJECT_DIR%teleprompter.py"
  exit /b 0
)

if exist "%PYTHON%" (
  start "" "%PYTHON%" "%PROJECT_DIR%teleprompter.py"
  exit /b 0
)

start "" pythonw "%PROJECT_DIR%teleprompter.py"
