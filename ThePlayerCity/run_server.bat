@echo off
title ThePlayerCity Server - Auto Bootstrapper
echo ===================================================
echo   ThePlayerCity Server Bootstrapper (Windows)
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 was not detected on your system.
    echo Please install Python 3 and add it to your PATH to run this project.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo [1/2] Installing requirements...
:: No external requirements are currently imported (it uses tkinter, asyncio, socket, struct),
:: but we run a dummy/basic pip validation just in case they add custom libraries later.
python -m pip install --upgrade pip

echo.
echo [2/2] Launching Server GUI ^& Engine...
echo.
python "%~dp0main.py"

pause
