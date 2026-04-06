# Pixel Cake 项目 - 会话上下文文档
# 下次会话时发送此文档给AI助手，以便继续项目

## 📋 项目状态

**项目名称**: Pixel Cake - AI修图工具
**GitHub仓库**: https://github.com/guihuaxiang1-cmd/pixel-cake
**启动日期**: 2026-04-05
**当前状态**: MVP已完成，3个关键bug已修复，待用户本地测试验证

## 👤 用户信息

- GitHub用户名: guihuaxiang1-cmd
- 操作系统: Windows
- 路径注意: 需要纯英文路径（原路径含中文字符）
- 前端修改后必须 `npm run build` 才能生效（或用 `npm run dev` 开发模式）

## ✅ 已完成功能

### AI修图（全部已实现后端API对接）
- [x] AI去路人（SAM2分割 + LaMa修复）
- [x] AI祛纹身（皮肤检测 + Inpainting）
- [x] AI去胡渣（面部关键点 + 皮肤融合）
- [x] AI消除穿帮（通用分割 + Inpainting）
- [x] AI补光（4种模式：自然/戏剧/柔光/逆光）
- [x] 换天空（6种预设 + 自定义天空图）
- [x] 牙齿美白（肤色检测 + 局部提亮）
- [x] AI补草地（地面检测 + 草地纹理）
- [x] AI追色 2.0（暂时用自动调色兜底，需参考图功能待完善）

### 色彩调色
- [x] 专业调色（16参数：曝光/对比/高光/阴影/色温/饱和度/vibrance/clarity等）
- [x] 局部调色（画笔/线性/径向/主体/背景）- UI已完成，后端对接待完善
- [x] 9款内置滤镜（青木胶片/暖咖画报/哈苏/徕卡/赛博朋克等）- 后端已支持

### 人像精修
- [x] 中性灰磨皮（双边滤波 + 光影分离 + 纹理保留）- 后端enhance.py已实现

### 工作流
- [x] 批量处理（拖拽上传→批量处理→进度条→一键下载）- 已修复
- [x] 前后对比（滑块式对比）
- [x] 撤销/重做
- [x] 画布缩放/平移
- [x] 导出（单张 + 批量下载）

## ❌ 待实现功能

### 高优先级
- [ ] 3D骨骼定位点美型（需要MediaPipe Face Mesh + 3D变形）
- [ ] 发丝级头发处理（祛碎发/换发色/光泽增强）
- [ ] 16bit Raw引擎（需要rawpy + 全链路16bit处理）
- [ ] AI追色需要导入参考图功能（当前是自动调色兜底）
- [ ] 局部调色的画笔/线性/径向蒙版后端实现

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
- FastAPI + Uvicorn（端口8765）
- PyTorch + OpenCV + Pillow + NumPy
- AI模型：
  - LaMa：图像修复（去路人等）~450MB
  - SAM2：语义分割 400MB~2.4GB
  - MediaPipe：人脸检测/分割 ~5MB
- 打包方案：PyInstaller（单文件exe，由launcher.py引导）

### 前端（React + TypeScript）
- Vite + React 18 + TailwindCSS
- 修改源码后需要 `npm run build` 编译，或用 `npm run dev` 热重载
- **重要**: run.bat 启动的是编译后的 dist 目录，不是 src 目录

### 组件结构
```
App.tsx           - 主应用，状态管理核心
├── Header.tsx    - 顶栏（上传/缩放/撤销/重做/对比/批量/导出）
├── Toolbar.tsx   - 左侧工具栏（选择/画笔/橡皮/裁剪/移动等）
├── Canvas.tsx    - 中间画布（图片渲染/画笔绘制/缩放平移）
├── Sidebar.tsx   - 右侧面板（基础/色彩/细节/滤镜/AI 5个Tab）
├── BeforeAfter.tsx - 前后对比滑块
└── BatchProcess.tsx - 批量处理面板
```

### 后端API端点
```
POST /api/upload          - 上传图片
GET  /api/image/{id}      - 获取图片
POST /api/auto-segment    - 自动分割（返回 X-Mask-Id header）
POST /api/inpaint         - 图像修复
POST /api/enhance         - 调色/滤镜/磨皮
POST /api/sky/replace     - 换天空
POST /api/relight         - 补光
POST /api/batch           - 批量处理
```

### 文件结构
```
pixel-cake/
├── run.bat                  # 快速启动（Python+Node一体化）
├── build.bat                # 打包exe
├── launcher.py              # 一体化启动器（自动装依赖、启动前后端）
├── pixel-cake.spec          # PyInstaller配置
├── backend/
│   ├── main.py              # 后端API（FastAPI路由）
│   ├── requirements.txt     # Python依赖
│   ├── services/
│   │   ├── inpainting.py    # LaMa修复引擎
│   │   ├── segmentation.py  # SAM2/MediaPipe分割
│   │   ├── sky.py           # 天空替换
│   │   └── enhance.py       # 调色/磨皮/滤镜（含FILTER_PRESETS）
│   └── utils/
│       └── image_utils.py   # 图像工具函数
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx          # ★ 主组件（状态管理）
│       ├── main.tsx
│       ├── index.css
│       └── components/
│           ├── Header.tsx
│           ├── Toolbar.tsx
│           ├── Canvas.tsx
│           ├── Sidebar.tsx
│           ├── BeforeAfter.tsx
│           └── BatchProcess.tsx
└── assets/
    └── icon.svg
```

## 🐛 已修复的Bug（2026-04-06 commit d3b325ab）

### Bug 1: 单张图AI功能点击无反应
- **根因**: `App.tsx` 的 `handleAIFeature` 只有3个case（remove-person/sky-replace/relight），其余6个AI功能没有分支
- **修复**: 补全全部9个AI功能的switch分支，每个功能都正确调用后端API并更新resultUrl
- **涉及文件**: `frontend/src/App.tsx`

### Bug 2: 批量处理后图片不显示
- **根因**: 后端返回错误时 `URL.createObjectURL(blob)` 生成无效URL，img标签加载失败
- **修复**: 增加HTTP状态码检查(`if (!res.ok) throw`)、img添加onError回退到预览图、处理失败标记为error状态
- **涉及文件**: `frontend/src/components/BatchProcess.tsx`

### Bug 3: 批量导出只能导第一张
- **根因**: "全部下载"按钮是空壳，没有onClick handler
- **修复**: 实现 `handleDownloadAll` — 遍历done状态图片逐个下载，间隔300ms防浏览器拦截
- **涉及文件**: `frontend/src/components/BatchProcess.tsx`

### Bug 4: 滤镜点击无反应
- **根因**: `handleFilter` 只设置了selectedFilter状态，没有调后端API
- **修复**: 添加fetch调用 `/api/enhance` 并传入filter参数
- **涉及文件**: `frontend/src/App.tsx`

### 后端同步修改
- `EnhanceRequest` 增加 `filter: Optional[str]` 和 `skin_smooth: bool` 字段
- `/enhance` 端点增加滤镜和磨皮处理分支
- **涉及文件**: `backend/main.py`

## ⚠️ 已知注意事项

1. **修改前端源码后必须重新构建**:
   ```bash
   cd frontend
   npm run build    # 编译到 dist/
   ```
   或用开发模式（自动刷新）：
   ```bash
   cd frontend && npm run dev
   cd backend && python main.py
   # 浏览器打开 http://localhost:5173
   ```

2. **Python 3.10+** 必须安装并勾选 Add to PATH

3. **AI模型首次使用自动下载**（LaMa ~450MB，SAM2 400MB~2.4GB）

4. **推荐NVIDIA GPU**（6GB+显存），CPU也可运行但较慢

5. **路径必须纯英文**，中文路径会导致Python/Node报错

6. **GitHub Token安全**: 曾有token在聊天中明文传递，已建议撤销。以后推送代码应使用环境变量或git credential manager

## 📝 Git提交历史

```
d3b325ab  2026-04-06  fix: 修复三个关键bug
84dbeaca  2026-04-06  fix: 修复AI功能无反应/批量处理/批量导出
58de1989  2026-04-05  Add session context document
b606e430  2026-04-05  Fix: robust Python detection and venv creation
32686c03  2026-04-05  Fix: batch files encoding and path issues
e33de3a9  2026-04-05  🎨 Pixel Cake 初始版本
```

## 🔄 下次继续开发时的检查清单

1. 确认用户已 pull 最新代码并成功 `npm run build`
2. 确认3个bug已修复（AI功能、批量显示、批量下载）
3. 了解用户新的需求或发现的新问题
4. 检查后端API端点是否完整（特别是局部调色、AI追色参考图）
