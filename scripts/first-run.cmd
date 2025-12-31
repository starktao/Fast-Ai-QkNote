@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

echo Running first-time setup...
call "%~dp0setup.cmd"
if errorlevel 1 exit /b 1

echo Starting services...
call "%~dp0start.cmd"

endlocal
exit /b 0
