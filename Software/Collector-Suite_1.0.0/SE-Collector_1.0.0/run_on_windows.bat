@echo off
setlocal
cd /d "%~dp0"
set "SUITE_DIR=%~dp0.."
set "PYTHON_BIN=%SUITE_DIR%\.venv\Scripts\python.exe"

if not "%~1"=="" (
  set "SE_COLLECTOR_WORKDIR=%~1"
) else (
  for /f "usebackq delims=" %%I in (`powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Unterrichtsordner fuer SE-Collector auswaehlen'; if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"`) do set "SE_COLLECTOR_WORKDIR=%%I"
)

if "%SE_COLLECTOR_WORKDIR%"=="" (
  echo Kein Arbeitsordner ausgewaehlt.
  goto :eof
)

for %%I in ("%SE_COLLECTOR_WORKDIR%") do set "SELECTED_WORKDIR=%%~fI"
for %%I in ("%~dp0.") do set "SOFTWARE_DIR=%%~fI"
if /I "%SELECTED_WORKDIR%"=="%SOFTWARE_DIR%" (
  echo Der Programmordner kann nicht als Unterrichtsordner verwendet werden.
  echo Bitte einen separaten Klassen- oder Unterrichtsordner auswaehlen.
  pause
  goto :eof
)

if not exist "%PYTHON_BIN%" (
  echo Gemeinsame Suite-Umgebung wird einmalig eingerichtet ...
  py -3 -m venv "%SUITE_DIR%\.venv"
  if errorlevel 1 goto :error
)

"%PYTHON_BIN%" -c "import fastapi, uvicorn, jinja2, multipart, qrcode, cv2, psutil, pypdf" >nul 2>&1
if errorlevel 1 (
  echo Fehlende Programmbestandteile werden einmalig installiert ...
  "%PYTHON_BIN%" -m pip install --upgrade pip
  "%PYTHON_BIN%" -m pip install -r "%SUITE_DIR%\requirements.txt"
  if errorlevel 1 goto :error
)

"%PYTHON_BIN%" app.py
goto :eof

:error
echo.
echo Einrichtung fehlgeschlagen. Bitte Python 3 installieren oder die Schul-IT kontaktieren.
pause
