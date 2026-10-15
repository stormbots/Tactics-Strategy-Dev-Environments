@echo off
setlocal
set "SDE_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "SDE_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%SDE_PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-SDE-Maintenance-Windows.ps1"
if errorlevel 1 (
  echo.
  echo Maintenance launcher did not complete. Read the error above.
  pause
)
endlocal
