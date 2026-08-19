@echo off
cd /d "%~dp0"
set "SUITE_DIR=%~dp0.."
set "PYTHON_BIN=%SUITE_DIR%\.venv\Scripts\python.exe"
:select_folder
if not defined QR_GENERATOR_WORKDIR (
  for /f "usebackq delims=" %%D in (`powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Persoenlichen Arbeitsordner mit Namensliste.ods auswaehlen'; if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"`) do set "QR_GENERATOR_WORKDIR=%%D"
)
if not defined QR_GENERATOR_WORKDIR exit /b 0
if not exist "%QR_GENERATOR_WORKDIR%\Namensliste.ods" (
  echo Im gewaehlten Ordner fehlt Namensliste.ods:
  echo %QR_GENERATOR_WORKDIR%
  pause
  exit /b 1
)
if not exist "%PYTHON_BIN%" py -3 -m venv "%SUITE_DIR%\.venv"
"%PYTHON_BIN%" -c "import fastapi,uvicorn,jinja2,multipart,qrcode,pypdf,psutil,cv2" >nul 2>&1
if errorlevel 1 "%PYTHON_BIN%" -m pip install -r "%SUITE_DIR%\requirements.txt"
"%PYTHON_BIN%" app.py
if errorlevel 23 if not errorlevel 24 (
  set "QR_GENERATOR_WORKDIR="
  set "QR_GENERATOR_SWITCHED=1"
  goto select_folder
)
pause
