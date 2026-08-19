@echo off
setlocal
cd /d "%~dp0"
set "SUITE_DIR=%~dp0.."
set "PYTHON_BIN=%SUITE_DIR%\.venv\Scripts\python.exe"

if not "%~1"=="" (
  set "HB_COLLECTOR_WORKDIR=%~1"
) else (
  for /f "usebackq delims=" %%I in (`powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Arbeitsordner fuer HB-Collector auswaehlen'; if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"`) do set "HB_COLLECTOR_WORKDIR=%%I"
)
if "%HB_COLLECTOR_WORKDIR%"=="" (
  echo Kein Arbeitsordner ausgewaehlt.
  goto :eof
)

if not exist "%PYTHON_BIN%" py -3 -m venv "%SUITE_DIR%\.venv"
"%PYTHON_BIN%" -c "import fastapi,uvicorn,jinja2,multipart,pypdf,qrcode,cv2,psutil" >nul 2>&1
if errorlevel 1 "%PYTHON_BIN%" -m pip install -r "%SUITE_DIR%\requirements.txt"
"%PYTHON_BIN%" app.py
pause
