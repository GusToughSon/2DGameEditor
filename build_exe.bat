@echo off
setlocal enabledelayedexpansion
title 2D Game Editor - Compiler
echo ========================================
echo   2D Game Editor Production Compiler
echo ========================================
echo.

:: Ensure we are in the script's directory
pushd "%~dp0"
set "APP_DIR=%~dp0"

:: Identify Python Command
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=py
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        :: Fallback to common user path or fail
        set PYTHON_CMD="C:\Users\gooro\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    )
)

:: 0. Dependency Check
echo [DEBUG] Verifying build environment...
    %PYTHON_CMD% -m pip install --upgrade pip nuitka pyinstaller zstandard Pillow pystray
    if %errorlevel% neq 0 ( echo [ERROR] Dependency install failed. & pause & exit /b 1 )
:: 1. Auto-Increment Version
for /f "tokens=*" %%v in ('%PYTHON_CMD% increment_version.py') do set APP_VER=%%v

:: 2. Setup Directories & Paths
if not exist dist mkdir dist
if not exist build mkdir build
set "ICON_PATH=%APP_DIR%Assets\EditorIcon.ico"

echo [DEBUG] Build Version: !APP_VER!
echo.
echo [1] Production Mode (Clean)
echo [2] Diagnostic Mode (Show Console) [DEFAULT in 2s]
choice /C 12 /D 2 /T 2 /M "Select Mode"
set MODE=%errorlevel%

set "CONSOLE_FLAG=--noconsole"
if "!MODE!"=="2" set "CONSOLE_FLAG=--console"

set "INFO_FILE=dist\version_info.txt"

:: Generate Professional Version Resource for Windows
set "VER_TUPLE=(!APP_VER:.=, !, 0)"

:: Generate Professional Version Resource for Windows
echo VSVersionInfo(> "%INFO_FILE%"
echo   ffi=FixedFileInfo(>> "%INFO_FILE%"
echo     filevers=%VER_TUPLE%,>> "%INFO_FILE%"
echo     prodvers=%VER_TUPLE%,>> "%INFO_FILE%"
echo     mask=0x3f,>> "%INFO_FILE%"
echo     flags=0x0,>> "%INFO_FILE%"
echo     OS=0x40004,>> "%INFO_FILE%"
echo     fileType=0x1,>> "%INFO_FILE%"
echo     subtype=0x0,>> "%INFO_FILE%"
echo     date=(0, 0)>> "%INFO_FILE%"
echo   ),>> "%INFO_FILE%"
echo   kids=[>> "%INFO_FILE%"
echo     StringFileInfo([>> "%INFO_FILE%"
echo       StringTable(>> "%INFO_FILE%"
echo         '040904B0', [>> "%INFO_FILE%"
echo           StringStruct('CompanyName', 'MacroIsFun LLC.'),>> "%INFO_FILE%"
echo           StringStruct('FileDescription', '2D Game Development Editor'),>> "%INFO_FILE%"
echo           StringStruct('FileVersion', '!APP_VER!'),>> "%INFO_FILE%"
echo           StringStruct('InternalName', '2DGameEditor'),>> "%INFO_FILE%"
echo           StringStruct('LegalCopyright', 'Copyright (c) 2026 MacroIsFun LLC.'),>> "%INFO_FILE%"
echo           StringStruct('OriginalFilename', '2DGameEditor.exe'),>> "%INFO_FILE%"
echo           StringStruct('ProductName', '2DGameEditor'),>> "%INFO_FILE%"
echo           StringStruct('ProductVersion', '!APP_VER!')>> "%INFO_FILE%"
echo         ])>> "%INFO_FILE%"
echo     ]),>> "%INFO_FILE%"
echo     VarFileInfo([VarStruct('Translation', [1033, 1200])])>> "%INFO_FILE%"
echo   ]>> "%INFO_FILE%"
echo )>> "%INFO_FILE%"

echo [DEBUG] Compiling Production Binary (Corporate Signature)...
%PYTHON_CMD% -m PyInstaller ^
    --onefile ^
    !CONSOLE_FLAG! ^
    --clean ^
    --icon="%ICON_PATH%" ^
    --add-data "%APP_DIR%Assets;Assets" ^
    --version-file="%INFO_FILE%" ^
    --runtime-tmpdir "%%LOCALAPPDATA%%\2DGameEditor" ^
    --distpath=dist ^
    --workpath=build ^
    --name="2DGameEditor_v!APP_VER!" ^
    GameEditor.py

if %errorlevel% neq 0 (
    echo [ERROR] Production Build failed.
    pause
) else (
    echo.
    echo [DEBUG] SUCCESS! Standalone Production EXE created in dist/
    
    REM Standard Cleanup
    if exist "build" rmdir /s /q "build"
    if exist "*.spec" del /q "*.spec"
    if exist "%INFO_FILE%" del /q "%INFO_FILE%"
)

popd
echo Build Process Complete.
pause
