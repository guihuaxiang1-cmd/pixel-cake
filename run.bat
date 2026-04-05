@echo off
chcp 65001 >nul 2>&1

echo.
echo ================================================
echo   Pixel Cake - AI Photo Editor
echo   Quick Start
echo ================================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM ===== [1/4] Check Python =====
echo [1/4] Checking Python...

set "PYTHON="

REM Try python3 first, then python
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto :python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :python_found
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py"
    goto :python_found
)

echo [ERROR] Python not found!
echo.
echo Please install Python 3.10+ from https://python.org
echo IMPORTANT: Check "Add Python to PATH" during install.
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do echo [OK] Found: %%i
echo    Using: %PYTHON%
echo.

REM ===== [2/4] Setup venv =====
echo [2/4] Setting up Python environment...

if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON% -m venv venv
    if errorlevel 1 (
        echo.
        echo [ERROR] venv creation failed. Trying alternative method...
        echo.
        REM Try installing venv module first
        %PYTHON% -m pip install virtualenv -q
        %PYTHON% -m virtualenv venv
        if errorlevel 1 (
            echo.
            echo [ERROR] Cannot create virtual environment.
            echo.
            echo Possible fixes:
            echo   1. Reinstall Python and CHECK "Add to PATH"
            echo   2. Run: pip install virtualenv
            echo   3. Try running this script as Administrator
            echo.
            echo Your Python info:
            %PYTHON% --version
            %PYTHON% -c "import sys; print(sys.executable)"
            echo.
            pause
            exit /b 1
        )
    )
)

REM Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv folder exists but activate.bat not found!
    echo Deleting broken venv and retrying...
    rmdir /s /q venv
    %PYTHON% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Still failed. Please check your Python installation.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
)

echo Installing dependencies (first run takes a few minutes)...
python -m pip install --upgrade pip -q 2>nul
python -m pip install fastapi uvicorn python-multipart opencv-python-headless Pillow numpy -q
if errorlevel 1 (
    echo.
    echo [WARNING] Some packages failed. Trying without -q for details...
    python -m pip install fastapi uvicorn python-multipart opencv-python-headless Pillow numpy
)

echo [OK] Python ready.
echo.

REM ===== [3/4] Build frontend =====
echo [3/4] Building frontend...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found!
    echo Please install from https://nodejs.org
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found!
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%\frontend"
if not exist "package.json" (
    echo [ERROR] package.json not found in frontend folder
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo Running npm install...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo Building...
call npm run build
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

if exist "frontend_dist" rmdir /s /q "frontend_dist"
xcopy /e /i /q "frontend\dist" "frontend_dist" >nul

echo [OK] Frontend built.
echo.

REM ===== [4/4] Start server =====
echo [4/4] Starting server...

if not exist "services" xcopy /e /i /q "backend\services" "services" >nul 2>&1
if not exist "utils" xcopy /e /i /q "backend\utils" "utils" >nul 2>&1
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs

echo.
echo ================================================
echo   Server running at http://127.0.0.1:8765
echo   Browser will open automatically...
echo   Press Ctrl+C to stop.
echo ================================================
echo.

python launcher.py

pause
