@echo off
setlocal
cd /d "%~dp0"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Bisherigen Collector-Suite-Ordner auswählen'; if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"`) do set "QUELLE=%%I"
if not defined QUELLE exit /b 0
py -3 upgrade_suite.py "%QUELLE%" --apply
echo.
pause
