@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "BACKEND_DIR=%ROOT%\backend"
set "FRONTEND_DIR=%ROOT%\frontend"
set "FFMPEG_EXE=%ROOT%\tools\ffmpeg\bin\ffmpeg.exe"

set "NEED_SETUP=0"
if not exist "%BACKEND_DIR%\.venv\Scripts\python.exe" set "NEED_SETUP=1"
if not exist "%FRONTEND_DIR%\node_modules" set "NEED_SETUP=1"
if not defined FFMPEG_LOCATION (
  if not exist "%FFMPEG_EXE%" (
    where ffmpeg >nul 2>nul
    if errorlevel 1 set "NEED_SETUP=1"
  )
)

if "%NEED_SETUP%"=="1" (
  echo Missing dependencies. Running setup...
  call "%~dp0setup.cmd"
  if errorlevel 1 exit /b 1
)

echo Starting backend...
start "Fast-Ai-QkNote Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"

echo Starting frontend...
start "Fast-Ai-QkNote Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev"

endlocal
exit /b 0
