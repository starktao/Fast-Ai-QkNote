@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

call :ensure_command python Python.Python.3.12 "Python 3.12+"
if errorlevel 1 exit /b 1
call :ensure_command node OpenJS.NodeJS.LTS "Node.js LTS"
if errorlevel 1 exit /b 1

set "TOOLS_DIR=%ROOT%\tools"
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"
set "FFMPEG_EXE=%FFMPEG_DIR%\bin\ffmpeg.exe"

if not exist "%FFMPEG_EXE%" (
  echo Downloading ffmpeg...
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $toolsDir='%TOOLS_DIR%'; New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null; $zipPath=Join-Path $toolsDir 'ffmpeg-release-essentials.zip'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $zipPath; Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force; $extractDir = Get-ChildItem -Path $toolsDir -Directory | Where-Object { $_.Name -like 'ffmpeg-*-essentials_build' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if (-not $extractDir) { throw 'ffmpeg archive layout unexpected.' }; $ffmpegDir = Join-Path $toolsDir 'ffmpeg'; if (-not (Test-Path $ffmpegDir)) { Move-Item -Path $extractDir.FullName -Destination $ffmpegDir }"
  if errorlevel 1 exit /b 1
)

set "BACKEND_DIR=%ROOT%\backend"
set "FRONTEND_DIR=%ROOT%\frontend"

echo Setting up backend virtual environment...
pushd "%BACKEND_DIR%"
if not exist ".venv" (
  python -m venv .venv
  if errorlevel 1 (popd & exit /b 1)
)
call ".venv\Scripts\activate.bat"
pip install -r requirements.txt
if errorlevel 1 (popd & exit /b 1)
if defined VIRTUAL_ENV call deactivate
popd

echo Installing frontend dependencies...
pushd "%FRONTEND_DIR%"
npm install
if errorlevel 1 (popd & exit /b 1)
popd

echo Setup completed.
endlocal
exit /b 0

:ensure_command
set "CMD_NAME=%~1"
set "WINGET_ID=%~2"
set "DISPLAY_NAME=%~3"
where %CMD_NAME% >nul 2>nul
if %errorlevel%==0 exit /b 0
where winget >nul 2>nul
if not %errorlevel%==0 (
  echo Missing %DISPLAY_NAME% and winget is not available. Install it manually and re-run this script.
  exit /b 1
)
echo Installing %DISPLAY_NAME% via winget...
winget install -e --id %WINGET_ID% --accept-source-agreements --accept-package-agreements
where %CMD_NAME% >nul 2>nul
if %errorlevel%==0 exit /b 0
echo %DISPLAY_NAME% install finished, but command not found. Restart the terminal and re-run this script.
exit /b 1
