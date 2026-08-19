@echo off
set "SOFTWARE_DIR=%~dp0"
set "PYTHON_BIN=%SOFTWARE_DIR%..\.venv\Scripts\python.exe"
cd /d "%SOFTWARE_DIR%"
if not exist "%PYTHON_BIN%" (
  echo Die Python-Umgebung fehlt. Bitte SE-Collector zuerst einmal mit run_on_windows.bat starten.
  pause
  exit /b 1
)
"%PYTHON_BIN%" test_ausgabe.py
if errorlevel 1 pause
