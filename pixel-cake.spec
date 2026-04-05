"""
Pixel Cake - PyInstaller 打包配置
生成单文件 Windows exe
"""

import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(SPECPATH) if 'SPECPATH' in dir() else Path(__file__).parent

block_cipher = None

# ─── 数据文件 ───
datas = [
    # 前端构建产物
    ('frontend_dist', 'frontend_dist'),
    # 服务模块
    ('backend/services', 'services'),
    ('backend/utils', 'utils'),
]

# ─── 隐藏导入 ───
hiddenimports = [
    # FastAPI / Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'starlette',
    'starlette.middleware',
    'starlette.staticfiles',
    'starlette.responses',
    'multipart',
    'pydantic',
    # 图像处理
    'cv2',
    'PIL',
    'PIL.Image',
    'numpy',
    'scipy',
    'skimage',
    # AI 模型
    'torch',
    'torchvision',
    'transformers',
    'diffusers',
    'accelerate',
    'mediapipe',
    'segment_anything',
    # 系统
    'webbrowser',
    'threading',
]

# ─── 分析 ───
a = Analysis(
    ['launcher.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'notebook',
        'jupyter',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ─── 去重 & 优化 ───
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ─── 打包为单文件 exe ───
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PixelCake',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # True=显示控制台窗口（方便看日志）; False=隐藏
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # 应用图标
)
