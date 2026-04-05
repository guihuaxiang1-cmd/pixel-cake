# Pixel Cake 项目 - 会话上下文文档
# 请在下次会话时发送此文档给AI助手，以便继续项目

## 📋 项目状态

**项目名称**: Pixel Cake - AI修图工具
**GitHub仓库**: https://github.com/guihuaxiang1-cmd/pixel-cake
**启动日期**: 2026-04-06
**当前状态**: MVP已搭建，等待安装Python后测试

## 👤 用户信息

- GitHub用户名: guihuaxiang1-cmd
- 操作系统: Windows
- 路径注意: 需要纯英文路径（原路径含中文字符）

## ✅ 已完成功能

### AI修图
- [x] AI去路人（SAM2分割 + LaMa修复）
- [x] AI祛纹身（皮肤检测 + Inpainting）
- [x] AI去胡渣（面部关键点 + 皮肤融合）
- [x] AI消除穿帮（通用分割 + Inpainting）
- [x] AI补光（4种模式：自然/戏剧/柔光/逆光）
- [x] 换天空（6种预设 + 自定义天空图）

### 色彩调色
- [x] 专业调色（16参数：曝光/对比/高光/阴影/色温/饱和度/vibrance/clarity等）
- [x] 局部调色（画笔/线性/径向/主体/背景）
- [x] AI追色 2.0（LAB直方图匹配 + 光影迁移）
- [x] 9款内置滤镜（青木胶片/暖咖画报/哈苏/徕卡/赛博朋克等）

### 人像精修
- [x] 中性灰磨皮（双边滤波 + 光影分离 + 纹理保留）
- [x] 牙齿美白（肤色检测 + 局部提亮）
- [x] 肤色检测

### 工作流
- [x] 批量处理（拖拽上传→批量处理→进度条→一键下载）
- [x] 前后对比（滑块式对比）
- [x] 撤销/重做
- [x] 画布缩放/平移

## ❌ 待实现功能

### 高优先级
- [ ] 3D骨骼定位点美型（需要MediaPipe Face Mesh + 3D变形）
- [ ] 发丝级头发处理（祛碎发/换发色/光泽增强）
- [ ] 16bit Raw引擎（需要rawpy + 全链路16bit处理）

### 中优先级
- [ ] AI智能体（自然语言指令修图）
- [ ] 联机拍摄支持（佳能/索尼/尼康协议）
- [ ] 云端协同（多端同步）

### 低优先级
- [ ] 手机版/iPad版
- [ ] 视频精修（像素吐司）
- [ ] 挑图助手（自动挑选好照片）

## 🛠️ 技术架构

### 后端（Python）
- FastAPI + Uvicorn
- PyTorch + OpenCV + Pillow
- AI模型：
  - LaMa：图像修复（去路人等）
  - SAM2：语义分割
  - MediaPipe：人脸检测/分割
- 打包方案：PyInstaller（单文件exe）

### 前端（React + TypeScript）
- Vite + React 18 + TailwindCSS
- 组件结构：
  - App.tsx：主应用状态管理
  - Header.tsx：顶栏（上传/缩放/撤销/导出）
  - Toolbar.tsx：左侧工具栏
  - Canvas.tsx：主画布编辑器
  - Sidebar.tsx：右侧面板（基础/色彩/细节/滤镜/AI 5个Tab）
  - BeforeAfter.tsx：前后对比
  - BatchProcess.tsx：批量处理

### 文件结构
```
pixel-cake/
├── run.bat              # 快速启动
├── build.bat            # 打包exe
├── launcher.py          # 一体化启动器
├── backend/
│   ├── main.py          # 独立后端API
│   ├── services/
│   │   ├── inpainting.py  # LaMa/SD修复
│   │   ├── segmentation.py # SAM2分割
│   │   ├── sky.py         # 天空替换
│   │   └── enhance.py     # 调色/磨皮/滤镜
│   └── utils/
├── frontend/src/
│   ├── App.tsx
│   └── components/
└── assets/
```

## 🐛 已知问题

1. **bat文件编码问题**：已解决（改为纯ASCII）
2. **Python未安装**：用户需先安装Python 3.10+并勾选Add to PATH
3. **路径中文问题**：需放到纯英文路径

## 📝 备注

- 用户曾提供GitHub token用于推送代码，已建议用户撤销该token
- 仓库已推送3次commit，代码完全同步
- 前端需要npm install和npm run build后才能运行
- AI模型首次使用会自动下载（LaMa约450MB，SAM2约400MB-2.4GB）
- 推荐NVIDIA GPU（6GB+显存），CPU也可运行但较慢
