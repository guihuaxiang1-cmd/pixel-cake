@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║                                                   ║
echo ║   🎨  Pixel Cake - 构建脚本                       ║
echo ║                                                   ║
echo ╚═══════════════════════════════════════════════════╝
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM ─── Step 1: 检查依赖 ───
echo [1/5] 检查环境依赖...

where node >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装: https://nodejs.org
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 npm
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo.

REM ─── Step 2: 构建前端 ───
echo [2/5] 构建前端...

cd /d "%PROJECT_DIR%\frontend"

if not exist "node_modules" (
    echo 📦 安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo ❌ npm install 失败
        pause
        exit /b 1
    )
)

echo 🔨 编译前端...
call npm run build
if errorlevel 1 (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)

REM 复制构建产物到根目录
cd /d "%PROJECT_DIR%"
if exist "frontend_dist" rmdir /s /q "frontend_dist"
xcopy /e /i /q "frontend\dist" "frontend_dist"

echo ✅ 前端构建完成
echo.

REM ─── Step 3: 安装 Python 依赖 ───
echo [3/5] 安装 Python 依赖...

pip install -r backend\requirements.txt -q
pip install pyinstaller -q

echo ✅ Python 依赖安装完成
echo.

REM ─── Step 4: 复制后端代码 ───
echo [4/5] 准备打包文件...

REM PyInstaller 需要服务模块在根目录
if exist "services" rmdir /s /q "services"
if exist "utils" rmdir /s /q "utils"
xcopy /e /i /q "backend\services" "services"
xcopy /e /i /q "backend\utils" "utils"

echo ✅ 文件准备完成
echo.

REM ─── Step 5: 打包 exe ───
echo [5/5] 打包为 Windows exe...
echo ⏳ 这可能需要几分钟，请耐心等待...

REM 生成图标（如果没有的话）
if not exist "assets" mkdir "assets"

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
    --hidden-import numpy ^
    --hidden-import torch ^
    --hidden-import torchvision ^
    --hidden-import transformers ^
    --hidden-import diffusers ^
    --hidden-import mediapipe ^
    --hidden-import accelerate ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module jupyter ^
    --exclude-module pytest ^
    launcher.py

if errorlevel 1 (
    echo ❌ 打包失败
    pause
    exit /b 1
)

echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║                                                   ║
echo ║   ✅  构建完成！                                   ║
echo ║                                                   ║
echo ║   📦  输出文件: dist\PixelCake.exe                ║
echo ║                                                   ║
echo ║   双击 dist\PixelCake.exe 即可运行                ║
echo ║                                                   ║
echo ╚═══════════════════════════════════════════════════╝
echo.

REM 打开输出目录
explorer dist

pause
