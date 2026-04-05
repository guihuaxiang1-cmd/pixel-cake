@echo off
chcp 65001 >nul 2>&1

echo.
echo ================================================
echo   Pixel Cake - AI Photo Editor
echo   Quick Start
echo ================================================
echo.

REM -- Get script directory --
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [1/4] Checking environment...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    echo         Make sure to check "Add to PATH" during installation.
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo [OK] Environment ready.
echo.

REM -- Create venv --
echo [2/4] Setting up Python environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo Installing Python dependencies (first time may take a few minutes)...
pip install fastapi uvicorn python-multipart opencv-python-headless Pillow numpy -q 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)

echo [OK] Python ready.
echo.

REM -- Build frontend --
echo [3/4] Building frontend...

cd /d "%PROJECT_DIR%\frontend"
if not exist "package.json" (
    echo [ERROR] frontend/package.json not found!
    echo Current directory: %cd%
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo Installing npm packages...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo Building React app...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

REM -- Copy build output --
if exist "frontend_dist" rmdir /s /q "frontend_dist"
xcopy /e /i /q "frontend\dist" "frontend_dist" >nul

echo [OK] Frontend built.
echo.

REM -- Prepare backend --
echo [4/4] Starting server...

REM Copy service modules to root for launcher.py
if not exist "services" (
    xcopy /e /i /q "backend\services" "services" >nul 2>&1
)
if not exist "utils" (
    xcopy /e /i /q "backend\utils" "utils" >nul 2>&1
)

REM Create needed directories
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs

echo.
echo ================================================
echo   Server starting at http://127.0.0.1:8765
echo   Browser will open automatically...
echo   Press Ctrl+C to stop.
echo ================================================
echo.

python launcher.py

pause
