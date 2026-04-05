@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║                                                   ║
echo ║   🎨  Pixel Cake - 快速启动                       ║
echo ║                                                   ║
echo ╚═══════════════════════════════════════════════════╝
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM ─── 检查 Python venv ───
if not exist "venv" (
    echo 📦 创建 Python 虚拟环境...
    python -m venv venv
)

REM ─── 激活 venv ───
call venv\Scripts\activate.bat

REM ─── 安装依赖 ───
echo 📦 检查依赖...
pip install -r backend\requirements.txt -q

REM ─── 构建前端（如果还没有构建过） ───
if not exist "frontend_dist" (
    echo 🔨 构建前端...
    cd frontend
    if not exist "node_modules" (
        call npm install
    )
    call npm run build
    cd /d "%PROJECT_DIR%"
    xcopy /e /i /q "frontend\dist" "frontend_dist"
)

REM ─── 复制后端模块 ───
if not exist "services" (
    xcopy /e /i /q "backend\services" "services"
)
if not exist "utils" (
    xcopy /e /i /q "backend\utils" "utils"
)

REM ─── 创建输出目录 ───
if not exist "uploads" mkdir "uploads"
if not exist "outputs" mkdir "outputs"

REM ─── 启动 ───
echo.
echo 🚀 启动中...
echo 🌐 浏览器将自动打开 http://127.0.0.1:8765
echo.
echo 按 Ctrl+C 停止服务
echo.

python launcher.py

pause
