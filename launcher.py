"""
Pixel Cake - Launcher
Serves frontend static files + API in one process.
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path


def get_base_dir():
    """Get resource base dir (compatible with PyInstaller)"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


def main():
    import uvicorn
    from fastapi import FastAPI, File, UploadFile, Form, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
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

    for d in [UPLOAD_DIR, OUTPUT_DIR]:
        d.mkdir(exist_ok=True)

    print(f"Base dir: {base}")
    print(f"Frontend: {FRONTEND_DIR} (exists: {FRONTEND_DIR.exists()})")

    app = FastAPI(title="Pixel Cake", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Lazy-loaded services
    _services = {}

    def get_service(name):
        if name not in _services:
            try:
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
            except Exception as e:
                print(f"[Warning] Failed to load {name}: {e}")
                _services[name] = None
        return _services.get(name)

    def load_image(path: str):
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Cannot load: {path}")
        return img

    # -- Models --
    class InpaintRequest(BaseModel):
        image_id: str
        mask_id: str
        prompt: str = ""
        strength: float = 0.8

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

    # -- API Routes --

    @app.get("/api/health")
    async def health():
        import torch
        return {
            "status": "ok",
            "gpu": torch.cuda.is_available(),
            "frontend": FRONTEND_DIR.exists(),
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
            raise HTTPException(404, "Image not found")
        return FileResponse(str(matches[0]))

    @app.post("/api/auto-segment")
    async def auto_segment(image_id: str = Form(...), mode: str = Form("person")):
        matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
        if not matches:
            raise HTTPException(404, "Image not found")
        img = load_image(str(matches[0]))
        seg = get_service("segmentation")
        if seg is None:
            # Fallback: return a full mask
            combined = np.zeros(img.shape[:2], dtype=np.uint8)
        else:
            masks = seg.auto_detect_people(img) if mode == "person" else (
                seg.auto_detect_sky(img) if mode == "sky" else seg.auto_detect_all(img))
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
            raise HTTPException(404, "Image not found")
        if not mask_matches:
            raise HTTPException(404, "Mask not found")
        img = load_image(str(img_matches[0]))
        mask = cv2.imread(str(mask_matches[0]), cv2.IMREAD_GRAYSCALE)
        inp = get_service("inpainting")
        if inp:
            result = inp.inpaint(img, mask, prompt=req.prompt)
        else:
            # Fallback: use OpenCV inpainting
            result = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
        rid = str(uuid.uuid4())[:8]
        rpath = OUTPUT_DIR / f"{rid}.jpg"
        cv2.imwrite(str(rpath), result)
        return FileResponse(str(rpath), headers={"X-Result-Id": rid})

    @app.post("/api/enhance")
    async def enhance(req: EnhanceRequest):
        matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
        if not matches:
            raise HTTPException(404, "Image not found")
        img = load_image(str(matches[0]))
        enh = get_service("enhance")
        if enh:
            result = enh.adjust(
                img, brightness=req.brightness, contrast=req.contrast,
                saturation=req.saturation, warmth=req.warmth,
                sharpness=req.sharpness, denoise=req.denoise,
            )
        else:
            result = img
        rid = str(uuid.uuid4())[:8]
        rpath = OUTPUT_DIR / f"{rid}.jpg"
        cv2.imwrite(str(rpath), result)
        return FileResponse(str(rpath))

    @app.post("/api/sky/replace")
    async def sky_replace(req: SkyReplaceRequest):
        matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
        if not matches:
            raise HTTPException(404, "Image not found")
        img = load_image(str(matches[0]))
        sky = get_service("sky")
        if sky:
            result = sky.replace(img, sky_type=req.sky_type, blend=req.blend_strength)
        else:
            result = img
        rid = str(uuid.uuid4())[:8]
        rpath = OUTPUT_DIR / f"{rid}.jpg"
        cv2.imwrite(str(rpath), result)
        return FileResponse(str(rpath))

    @app.post("/api/relight")
    async def relight(image_id: str = Form(...), brightness: float = Form(0.3), warmth: float = Form(0.1)):
        matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
        if not matches:
            raise HTTPException(404, "Image not found")
        img = load_image(str(matches[0]))
        enh = get_service("enhance")
        if enh:
            result = enh.relight(img, brightness=brightness, warmth=warmth)
        else:
            result = np.clip(img.astype(np.float32) + brightness * 150, 0, 255).astype(np.uint8)
        rid = str(uuid.uuid4())[:8]
        rpath = OUTPUT_DIR / f"{rid}.jpg"
        cv2.imwrite(str(rpath), result)
        return FileResponse(str(rpath))

    # -- Frontend --
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        @app.get("/")
        async def root():
            return FileResponse(str(FRONTEND_DIR / "index.html"))

        # Serve static assets
        if (FRONTEND_DIR / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

        @app.api_route("/{full_path:path}", methods=["GET"], include_in_schema=False)
        async def spa_fallback(full_path: str):
            file_path = FRONTEND_DIR / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(FRONTEND_DIR / "index.html"))
    else:
        @app.get("/")
        async def root_fallback():
            return {
                "message": "Pixel Cake API is running.",
                "note": "Frontend not built yet. Run: cd frontend && npm run build"
            }

    # -- Start --
    host = "127.0.0.1"
    port = 8765
    url = f"http://{host}:{port}"

    print()
    print("=" * 50)
    print(f"  Pixel Cake - AI Photo Editor")
    print(f"  URL: {url}")
    print("=" * 50)
    print()

    def open_browser_delayed():
        time.sleep(2)
        webbrowser.open(url)

    threading.Thread(target=open_browser_delayed, daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
