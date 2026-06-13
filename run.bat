@echo off
:: 2DGameEditor Launcher
:: ===============================================================================
setlocal EnableExtensions EnableDelayedExpansion

:: Change directory to the script's folder
pushd "%~dp0"

:: 2. Set console aesthetics and branding
title 2DGameEditor Bootstrapper [Node: %COMPUTERNAME%]
color 0A

echo ==============================================================================
echo [INFO] Bootstrapping 2DGameEditor Environment
echo [INFO] Working Directory: %CD%
echo ==============================================================================

:: 3. Locate the correct Python interpreter dynamically
set "PYTHON_BIN="

:: Priority lookup: 'py' (Windows Launcher) -> 'python3' -> 'python'
for %%X in (py python3 python) do (
    where %%X >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_BIN=%%X"
        goto :FoundPython
    )
)

:NoPython
color 4F
echo [FATAL] Python interpreter not found in system PATH.
echo [FATAL] Please install Python 3 (https://www.python.org/) and check "Add to PATH".
pause
popd
exit /B 1

:FoundPython
echo [INFO] Python Interpreter mounted: '!PYTHON_BIN!'
!PYTHON_BIN! --version

:: Check if requirements are installed, if not install them
echo [INFO] Checking dependencies...
!PYTHON_BIN! -c "import PIL, pystray" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [INFO] Installing missing dependencies (Pillow, pystray)
    !PYTHON_BIN! -m pip install Pillow pystray
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to install dependencies. The application might fail to start.
    )
)

:: 4. Execution & Handoff
echo [INFO] Terminating existing instances...
:: Target only windows with the specific '[Active Engine]' tag to avoid closing other editors.
taskkill /F /FI "WINDOWTITLE eq 2DGameEditor [Active Engine]*" /T >nul 2>&1

echo [INFO] Handing off control to Python runtime...
echo.
echo =========================== SYSTEM LOG =======================================

:: Execute the payload (Console remains open for debug streaming)
!PYTHON_BIN! GameEditor.py

:: Capture the exact exit code of the Python process
set EXIT_CODE=!ERRORLEVEL!
echo ==============================================================================

:: 5. Process Exit Status and Telemetry
if !EXIT_CODE! NEQ 0 (
    color 0C
    echo [CRITICAL] Application terminated abnormally. (Exit Code: !EXIT_CODE!)
    echo [CRITICAL] Please review the stack trace above.
    pause
) else (
    echo [INFO] Process completed gracefully. (Exit Code: 0)
    :: Give the user 2 seconds to read the final log, then smoothly close.
    timeout /t 2 >nul
)

:: Restore original working directory and flush memory
popd
endlocal
::exit /B !EXIT_CODE!