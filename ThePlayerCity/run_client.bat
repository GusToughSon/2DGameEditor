@echo off
title ThePlayerCity Client Launcher
echo ===================================================
echo   ThePlayerCity Launcher (Windows)
echo ===================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 was not detected on your system.
    echo Please install Python 3 and add it to your PATH to run this project.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [1/1] Launching Launcher UI...
cd /d "%~dp0"
python -m client.launcher

pause
