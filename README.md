# 🎨 Pixel Cake - AI 修图工具

一款本地运行的AI智能修图软件，类似像素蛋糕的功能。

## ⚡ 快速启动（Windows）

### 方式一：直接运行（推荐测试）

1. 确保安装了 **Python 3.10+** 和 **Node.js 18+**
2. 双击 **`run.bat`**
3. 浏览器自动打开 `http://127.0.0.1:8765`

### 方式二：打包为 exe

1. 双击 **`build.bat`**
2. 等待构建完成（首次约5-10分钟）
3. 生成的 exe 在 `dist\PixelCake.exe`
4. 双击即可运行，无需安装任何依赖

## ✨ 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| AI去路人 | ✅ | SAM2分割 + LaMa修复 |
| AI祛纹身 | ✅ | 皮肤检测 + Inpainting |
| AI去胡渣 | ✅ | 面部关键点 + 皮肤融合 |
| AI消除穿帮 | ✅ | 通用分割 + Inpainting |
| AI补光 | ✅ | 4种模式（自然/戏剧/柔光/逆光） |
| 换天空 | ✅ | 6种预设 + 自定义天空图 |
| 中性灰磨皮 | ✅ | 光影分离 + 纹理保留 |
| 智能调色 | ✅ | 16个参数（Lightroom风格） |
| 局部调色 | ✅ | 画笔/线性/径向/主体/背景 |
| AI追色 2.0 | ✅ | LAB直方图匹配 + 光影迁移 |
| 滤镜预设 | ✅ | 9款（青木胶片/哈苏/徕卡等） |
| 批量处理 | ✅ | 拖拽上传→批量处理→一键下载 |
| 前后对比 | ✅ | 滑块式对比 |
| 牙齿美白 | ✅ | 自动检测 + 美白 |

## 🛠️ 技术栈

- **后端**: Python 3.10+ / FastAPI / PyTorch
- **前端**: React 18 + TypeScript + TailwindCSS
- **AI模型**: LaMa / SAM2 / MediaPipe / OpenCV
- **打包**: PyInstaller (单文件exe)

## 📁 项目结构

```
pixel-cake/
├── run.bat                ← 快速启动
├── build.bat              ← 打包为 exe
├── launcher.py            ← 一体化启动器
├── pixel-cake.spec        ← PyInstaller 配置
├── backend/
│   ├── main.py            ← 独立后端（开发用）
│   ├── requirements.txt
│   ├── services/
│   │   ├── inpainting.py  ← LaMa/SD 修复引擎
│   │   ├── segmentation.py← SAM2/MediaPipe 分割
│   │   ├── sky.py         ← 天空替换
│   │   └── enhance.py     ← 调色/磨皮/滤镜
│   └── utils/
├── frontend/
│   └── src/
│       ├── App.tsx        ← 主应用
│       └── components/    ← UI 组件
├── assets/
│   └── icon.svg           ← 应用图标
└── README.md
```

## 🔧 开发模式

```bash
# 后端（热重载）
cd backend
pip install -r requirements.txt
python main.py

# 前端（热重载）
cd frontend
npm install
npm run dev
```

## ⚙️ 模型说明

首次使用AI功能时会自动下载模型：

| 模型 | 大小 | 用途 |
|------|------|------|
| LaMa | ~450MB | 图像修复（去路人等） |
| SAM2 | ~400MB~2.4GB | 语义分割 |
| MediaPipe | ~5MB | 人物检测（轻量兜底） |

建议使用 **NVIDIA GPU**（6GB+ 显存），CPU 也可运行但较慢。

## License

MIT
