@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo O ambiente ainda nao foi preparado: a executar setup.bat primeiro...
    call setup.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" main.py %*
