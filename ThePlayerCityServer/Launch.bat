@echo off
title ThePlayerCity - Launcher
echo ==========================================
echo    ThePlayerCity - Launcher
echo ==========================================

echo [DEBUG] Cleaning up old processes...
taskkill /f /im caddy.exe /t 2>nul
taskkill /f /im python.exe /t 2>nul
taskkill /f /im py.exe /t 2>nul

echo [DEBUG] Starting HTTPS Proxy (Caddy)...
cd /d "%~dp0"
start "" /b "C:\Caddy\caddy.exe" run --config Caddyfile

echo [DEBUG] Starting Game Server...
echo ------------------------------------------
echo    Access the game at: http://localhost:8000
echo ------------------------------------------

:: Check and run server
set PY_CMD=
where py >nul 2>nul && set PY_CMD=py
if not defined PY_CMD (
    where python >nul 2>nul && set PY_CMD=python
)

%PY_CMD% server.py
pause
