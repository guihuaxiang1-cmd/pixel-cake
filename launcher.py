"""
Pixel Cake - 一体化启动器
前端静态文件由 FastAPI 直接托管，无需额外启动前端服务
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path


def get_base_dir():
    """获取资源根目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def setup_dirs():
    """创建必要目录"""
    base = get_base_dir()
    for d in ['uploads', 'outputs', 'assets/sky_images']:
        (base / d).mkdir(parents=True, exist_ok=True)


def create_app():
    """创建 FastAPI 应用（带静态文件托管）"""
    from fastapi import FastAPI, File, UploadFile, Form, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from typing import Optional
    import io
    import uuid

    import cv2
    import numpy as np
    from PIL import Image

    base = get_base_dir()
    UPLOAD_DIR = base / "uploads"
    OUTPUT_DIR = base / "outputs"
    FRONTEND_DIR = base / "frontend_dist"
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    app = FastAPI(title="Pixel Cake", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── 延迟加载服务 ───
    _services = {}

    def get_service(name):
        if name not in _services:
            if name == "inpainting":
                from services.inpainting import InpaintingService
                _services[name] = InpaintingService()
            elif name == "segmentation":
                from services.segmentation import SegmentationService
                _services[name] = SegmentationService()
            elif name == "sky":
                from services.sky import SkyService
                _services[name] = SkyService()
            elif name == "enhance":
                from services.enhance import EnhanceService
                _services[name] = EnhanceService()
        return _services.get(name)

    # ─── 数据模型 ───

    class InpaintRequest(BaseModel):
        image_id: str
        mask_id: str
        prompt: str = ""
        negative_prompt: str = "blurry, artifacts"
        strength: float = 0.8
        guidance_scale: float = 7.5
        steps: int = 30

    class SkyReplaceRequest(BaseModel):
        image_id: str
        sky_type: str = "sunset"
        blend_strength: float = 0.7

    class EnhanceRequest(BaseModel):
        image_id: str
        brightness: float = 0.0
        contrast: float = 0.0
        saturation: float = 0.0
        warmth: float = 0.0
        sharpness: float = 0.0
        denoise: float = 0.0

    class BatchRequest(BaseModel):
        image_ids: list[str]
        action: str
        params: dict = {}

    def load_image(path: str) -> np.ndarray:
        import cv2
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"无法加载: {path}")
        return img

    # ─── API 路由 ───

    @app.get("/api/health")
    async def health():
        import torch
        return {
            "status": "ok",
            "gpu": torch.cuda.is_available(),
            "version": "0.1.0",
        }

    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        image_id = str(uuid.uuid4())[:8]
        ext = Path(file.filename).suffix or ".jpg"
        save_path = UPLOAD_DIR / f"{image_id}{ext}"
        content = await file.read()
        save_path.write_bytes(content)
        img = Image.open(io.BytesIO(content))
        w, h = img.size
        return {"image_id": image_id, "filename": file.filename, "width": w, "height": h}

    @app.get("/api/image/{image_id}")
    async def get_image(image_id: str):
        matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
        if not matches:
            matches = list(OUTPUT_DIR.glob(f"{image_id}.*"))
        if not matches:
            raise HTTPException(404, "图片不存在")
        return FileResponse(str(matches[0]))

    @app.post("/api/auto-segment")
    async def auto_segment(image_id: str = Form(...), mode: str = Form("person")):
        matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
        if not matches:
            raise HTTPException(404, "图片不存在")
        img = load_image(str(matches[0]))
        seg = get_service("segmentation")
        if mode == "person":
            masks = seg.auto_detect_people(img)
        elif mode == "sky":
            masks = seg.auto_detect_sky(img)
        else:
            masks = seg.auto_detect_all(img)

        if masks:
            combined = np.zeros_like(masks[0])
            for m in masks:
                combined = np.maximum(combined, m)
        else:
            combined = np.zeros(img.shape[:2], dtype=np.uint8)

        mask_id = str(uuid.uuid4())[:8]
        mask_path = OUTPUT_DIR / f"{mask_id}_mask.png"
        cv2.imwrite(str(mask_path), combined)
        return FileResponse(str(mask_path), headers={"X-Mask-Id": mask_id})

    @app.post("/api/inpaint")
    async def inpaint(req: InpaintRequest):
        img_matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
        mask_matches = list(OUTPUT_DIR.glob(f"{req.mask_id}_mask.png"))
        if not img_matches:
            raise HTTPException(404, "原图不存在")
        if not mask_matches:
            raise HTTPException(404, "掩码不存在")
        img = load_image(str(img_matches[0]))
        mask = cv2.imread(str(mask_matches[0]), cv2.IMREAD_GRAYSCALE)
        inp = get_service("inpainting")
        result = inp.inpaint(img, mask, prompt=req.prompt)
        result_id = str(uuid.uuid4())[:8]
        result_path = OUTPUT_DIR / f"{result_id}.jpg"
        cv2.imwrite(str(result_path), result)
        return FileResponse(str(result_path), headers={"X-Result-Id": result_id})

    @app.post("/api/enhance")
    async def enhance(req: EnhanceRequest):
        matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
        if not matches:
            raise HTTPException(404, "图片不存在")
        img = load_image(str(matches[0]))
        enh = get_service("enhance")
        result = enh.adjust(
            img, brightness=req.brightness, contrast=req.contrast,
            saturation=req.saturation, warmth=req.warmth,
            sharpness=req.sharpness, denoise=req.denoise,
        )
        result_id = str(uuid.uuid4())[:8]
        result_path = OUTPUT_DIR / f"{result_id}.jpg"
        cv2.imwrite(str(result_path), result)
        return FileResponse(str(result_path))

    @app.post("/api/sky/replace")
    async def sky_replace(req: SkyReplaceRequest):
        matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
        if not matches:
            raise HTTPException(404, "图片不存在")
        img = load_image(str(matches[0]))
        sky = get_service("sky")
        result = sky.replace(img, sky_type=req.sky_type, blend=req.blend_strength)
        result_id = str(uuid.uuid4())[:8]
        result_path = OUTPUT_DIR / f"{result_id}.jpg"
        cv2.imwrite(str(result_path), result)
        return FileResponse(str(result_path))

    @app.post("/api/relight")
    async def relight(image_id: str = Form(...), brightness: float = Form(0.3), warmth: float = Form(0.1)):
        matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
        if not matches:
            raise HTTPException(404, "图片不存在")
        img = load_image(str(matches[0]))
        enh = get_service("enhance")
        result = enh.relight(img, brightness=brightness, warmth=warmth)
        result_id = str(uuid.uuid4())[:8]
        result_path = OUTPUT_DIR / f"{result_id}.jpg"
        cv2.imwrite(str(result_path), result)
        return FileResponse(str(result_path))

    @app.post("/api/batch")
    async def batch(req: BatchRequest):
        results = []
        for img_id in req.image_ids:
            matches = list(UPLOAD_DIR.glob(f"{img_id}.*"))
            if not matches:
                results.append({"image_id": img_id, "status": "not_found"})
                continue
            try:
                img = load_image(str(matches[0]))
                if req.action == "enhance":
                    enh = get_service("enhance")
                    result = enh.adjust(img, **req.params)
                elif req.action == "auto_remove":
                    seg = get_service("segmentation")
                    inp = get_service("inpainting")
                    masks = seg.auto_detect_people(img)
                    if masks:
                        combined = np.zeros_like(masks[0])
                        for m in masks:
                            combined = np.maximum(combined, m)
                        result = inp.inpaint(img, combined)
                    else:
                        result = img
                else:
                    results.append({"image_id": img_id, "status": "unknown"})
                    continue
                rid = str(uuid.uuid4())[:8]
                cv2.imwrite(str(OUTPUT_DIR / f"{rid}.jpg"), result)
                results.append({"image_id": img_id, "result_id": rid, "status": "ok"})
            except Exception as e:
                results.append({"image_id": img_id, "status": "error", "message": str(e)})
        return {"results": results}

    # ─── 前端静态文件托管 ───
    if FRONTEND_DIR.exists():
        @app.get("/")
        async def root():
            return FileResponse(str(FRONTEND_DIR / "index.html"))

        # 挂载静态资源
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

        # SPA fallback - 所有非API路径返回 index.html
        @app.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
        async def spa_fallback(path: str):
            file_path = FRONTEND_DIR / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(FRONTEND_DIR / "index.html"))
    else:
        @app.get("/")
        async def root_no_frontend():
            return {"message": "Pixel Cake API 正在运行。前端未构建。"}

    return app


def open_browser(url: str, delay: float = 2.0):
    """延迟打开浏览器"""
    time.sleep(delay)
    webbrowser.open(url)


def main():
    import uvicorn

    setup_dirs()
    app = create_app()
    host = "127.0.0.1"
    port = 8765
    url = f"http://{host}:{port}"

    print(f"""
╔══════════════════════════════════════════════╗
║                                              ║
║   🎨  Pixel Cake - AI 修图工具               ║
║                                              ║
║   地址: {url:<37s}║
║   正在启动...                                 ║
║                                              ║
╚══════════════════════════════════════════════╝
    """)

    # 自动打开浏览器
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
