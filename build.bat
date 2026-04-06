@echo off
chcp 65001 >nul 2>&1

echo.
echo ================================================
echo   Pixel Cake - Build Windows EXE
echo ================================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [1/5] Checking environment...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    pause
    exit /b 1
)

echo [OK] Environment ready.
echo.

echo [2/5] Building frontend...

cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    call npm install
)
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"
if exist "frontend_dist" rmdir /s /q "frontend_dist"
xcopy /e /i /q "frontend\dist" "frontend_dist" >nul

echo [OK] Frontend built.
echo.

echo [3/5] Installing Python packages...
call pip install fastapi uvicorn python-multipart opencv-python-headless Pillow numpy pyinstaller -q
echo [OK] Done.
echo.

echo [4/5] Preparing files...
if exist "services" rmdir /s /q "services"
if exist "utils" rmdir /s /q "utils"
xcopy /e /i /q "backend\services" "services" >nul
xcopy /e /i /q "backend\utils" "utils" >nul
echo [OK] Done.
echo.

echo [5/5] Packaging EXE (this may take several minutes)...
echo.

pyinstaller ^
    --name PixelCake ^
    --onefile ^
    --console ^
    --add-data "frontend_dist;frontend_dist" ^
    --add-data "services;services" ^
    --add-data "utils;utils" ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import fastapi ^
    --hidden-import fastapi.middleware ^
    --hidden-import fastapi.middleware.cors ^
    --hidden-import starlette ^
    --hidden-import starlette.middleware ^
    --hidden-import starlette.staticfiles ^
    --hidden-import starlette.responses ^
    --hidden-import multipart ^
    --hidden-import pydantic ^
    --hidden-import cv2 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import numpy ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module jupyter ^
    --exclude-module pytest ^
    launcher.py

if errorlevel 1 (
    echo [ERROR] Packaging failed.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   BUILD SUCCESS!
echo   Output: dist\PixelCake.exe
echo   Double-click to run!
echo ================================================
echo.

explorer dist
pause
