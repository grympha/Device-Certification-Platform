@echo off
setlocal

cd /d "%~dp0"

echo Installing Windows certification app dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  exit /b 1
)

set ICON_ARG=
if exist app.ico set ICON_ARG=--icon app.ico

echo Building LMX-Windows-Certification.exe...
python -m PyInstaller --onefile --windowed --name LMX-Windows-Certification %ICON_ARG% windows_certification_ui.py
if errorlevel 1 (
  echo EXE build failed.
  exit /b 1
)

echo Build complete:
echo %CD%\dist\LMX-Windows-Certification.exe
endlocal
