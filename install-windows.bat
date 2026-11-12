@echo off
rem One-click launcher for the Windows installer. Double-click it, or run from cmd.
rem Pass switches through, e.g.:  install-windows.bat -Guard -Enforce
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\install-windows.ps1" %*
set EC=%ERRORLEVEL%
echo.
echo Installer exited with code %EC%. See install-report.json for per-step results.
pause
endlocal
exit /b %EC%
