"""
Pixel Cake - AI 修图工具后端
基于 FastAPI + PyTorch，提供AI修图服务
"""

import os
import io
import uuid
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from services.inpainting import InpaintingService
from services.segmentation import SegmentationService
from services.sky import SkyService
from services.enhance import EnhanceService
from utils.image_utils import (
    load_image, save_image, image_to_bytes,
    resize_for_display, create_mask_from_points
)

# ──────────────────────────────────────────────
# App 初始化
# ──────────────────────────────────────────────

app = FastAPI(title="Pixel Cake API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储目录
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 全局服务实例（延迟加载）
inpainting: Optional[InpaintingService] = None
segmentation: Optional[SegmentationService] = None
sky_service: Optional[SkyService] = None
enhance_service: Optional[EnhanceService] = None


def get_inpainting() -> InpaintingService:
    global inpainting
    if inpainting is None:
        inpainting = InpaintingService()
    return inpainting


def get_segmentation() -> SegmentationService:
    global segmentation
    if segmentation is None:
        segmentation = SegmentationService()
    return segmentation


def get_sky() -> SkyService:
    global sky_service
    if sky_service is None:
        sky_service = SkyService()
    return sky_service


def get_enhance() -> EnhanceService:
    global enhance_service
    if enhance_service is None:
        enhance_service = EnhanceService()
    return enhance_service


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

class MaskRequest(BaseModel):
    """基于点击坐标的掩码请求"""
    image_id: str
    points: list[dict]  # [{"x": 100, "y": 200, "label": 1}]
    box: Optional[dict] = None  # {"x1": 0, "y1": 0, "x2": 100, "y2": 100}


class InpaintRequest(BaseModel):
    """图像修复请求"""
    image_id: str
    mask_id: str
    prompt: str = ""
    negative_prompt: str = "blurry, artifacts, low quality"
    strength: float = 0.8
    guidance_scale: float = 7.5
    steps: int = 30


class SkyReplaceRequest(BaseModel):
    """天空替换请求"""
    image_id: str
    sky_type: str = "sunset"  # sunset, blue, cloudy, starry, custom
    blend_strength: float = 0.7


class EnhanceRequest(BaseModel):
    """图像增强请求"""
    image_id: str
    brightness: float = 0.0    # -1 ~ 1
    contrast: float = 0.0      # -1 ~ 1
    saturation: float = 0.0    # -1 ~ 1
    warmth: float = 0.0        # -1 ~ 1
    sharpness: float = 0.0     # 0 ~ 1
    denoise: float = 0.0       # 0 ~ 1
    filter: Optional[str] = None     # 滤镜名称
    skin_smooth: bool = False  # 是否磨皮


class BatchRequest(BaseModel):
    """批量处理请求"""
    image_ids: list[str]
    action: str  # remove_person, remove_tattoo, enhance, sky_replace
    params: dict = {}


# ──────────────────────────────────────────────
# API 路由
# ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {"name": "Pixel Cake API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """健康检查 & GPU状态"""
    import torch
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    return {
        "status": "ok",
        "gpu": {"available": gpu_available, "name": gpu_name},
        "models_loaded": {
            "inpainting": inpainting is not None,
            "segmentation": segmentation is not None,
            "sky": sky_service is not None,
            "enhance": enhance_service is not None,
        }
    }


# ─── 图片上传 ───

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传图片，返回 image_id"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "仅支持图片文件")

    image_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".jpg"
    save_path = UPLOAD_DIR / f"{image_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    # 获取图片信息
    img = Image.open(io.BytesIO(content))
    w, h = img.size

    return {
        "image_id": image_id,
        "filename": file.filename,
        "width": w,
        "height": h,
        "path": str(save_path),
    }


@app.get("/image/{image_id}")
async def get_image(image_id: str, max_size: int = 2048):
    """获取图片（支持缩放）"""
    matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
    if not matches:
        matches = list(OUTPUT_DIR.glob(f"{image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = Image.open(matches[0]).convert("RGB")
    if max(img.size) > max_size:
        img = resize_for_display(img, max_size)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg")


# ─── AI 分割 ───

@app.post("/segment")
async def segment_object(req: MaskRequest):
    """
    使用SAM2进行交互式分割
    传入点击坐标，返回掩码
    """
    matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = load_image(str(matches[0]))
    seg = get_segmentation()

    points = [(p["x"], p["y"], p.get("label", 1)) for p in req.points]
    box = None
    if req.box:
        box = (req.box["x1"], req.box["y1"], req.box["x2"], req.box["y2"])

    mask = seg.predict(img, points=points, box=box)

    # 保存掩码
    mask_id = str(uuid.uuid4())[:8]
    mask_path = OUTPUT_DIR / f"{mask_id}_mask.png"
    cv2.imwrite(str(mask_path), mask)

    # 返回掩码预览
    mask_img = Image.fromarray(mask)
    buf = io.BytesIO()
    mask_img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png", headers={
        "X-Mask-Id": mask_id,
        "X-Width": str(mask.shape[1]),
        "X-Height": str(mask.shape[0]),
    })


@app.post("/auto-segment")
async def auto_segment(
    image_id: str = Form(...),
    mode: str = Form("person"),  # person, sky, all
):
    """自动分割（无需点击）"""
    matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = load_image(str(matches[0]))
    seg = get_segmentation()

    if mode == "person":
        masks = seg.auto_detect_people(img)
    elif mode == "sky":
        masks = seg.auto_detect_sky(img)
    else:
        masks = seg.auto_detect_all(img)

    # 合并所有掩码
    if masks:
        combined = np.zeros_like(masks[0])
        for m in masks:
            combined = np.maximum(combined, m)
    else:
        combined = np.zeros(img.shape[:2], dtype=np.uint8)

    mask_id = str(uuid.uuid4())[:8]
    mask_path = OUTPUT_DIR / f"{mask_id}_mask.png"
    cv2.imwrite(str(mask_path), combined)

    mask_img = Image.fromarray(combined)
    buf = io.BytesIO()
    mask_img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png", headers={
        "X-Mask-Id": mask_id,
        "X-Count": str(len(masks)),
    })


# ─── AI 修复（去路人 / 去纹身 / 去胡渣 / 消除穿帮） ───

@app.post("/inpaint")
async def inpaint(req: InpaintRequest):
    """
    AI图像修复 - 核心功能
    去路人、去纹身、去胡渣、消除穿帮都走这个接口
    """
    # 查找原图
    img_matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
    if not img_matches:
        raise HTTPException(404, "原图不存在")

    mask_matches = list(OUTPUT_DIR.glob(f"{req.mask_id}_mask.png"))
    if not mask_matches:
        raise HTTPException(404, "掩码不存在")

    img = load_image(str(img_matches[0]))
    mask = cv2.imread(str(mask_matches[0]), cv2.IMREAD_GRAYSCALE)

    inp = get_inpainting()
    result = inp.inpaint(
        image=img,
        mask=mask,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        strength=req.strength,
        guidance_scale=req.guidance_scale,
        num_steps=req.steps,
    )

    # 保存结果
    result_id = str(uuid.uuid4())[:8]
    result_path = OUTPUT_DIR / f"{result_id}.jpg"
    cv2.imwrite(str(result_path), result)

    buf = io.BytesIO()
    Image.fromarray(result).save(buf, format="JPEG", quality=95)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/jpeg", headers={
        "X-Result-Id": result_id,
    })


# ─── AI 补光 ───

@app.post("/relight")
async def relight(
    image_id: str = Form(...),
    brightness: float = Form(0.3),
    warmth: float = Form(0.1),
):
    """AI补光"""
    matches = list(UPLOAD_DIR.glob(f"{image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = load_image(str(matches[0]))
    enh = get_enhance()
    result = enh.relight(img, brightness=brightness, warmth=warmth)

    result_id = str(uuid.uuid4())[:8]
    result_path = OUTPUT_DIR / f"{result_id}.jpg"
    cv2.imwrite(str(result_path), result)

    buf = io.BytesIO()
    Image.fromarray(result).save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg")


# ─── 换天空 ───

@app.post("/sky/replace")
async def replace_sky(req: SkyReplaceRequest):
    """AI换天空"""
    matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = load_image(str(matches[0]))
    sky = get_sky()
    result = sky.replace(img, sky_type=req.sky_type, blend=req.blend_strength)

    result_id = str(uuid.uuid4())[:8]
    result_path = OUTPUT_DIR / f"{result_id}.jpg"
    cv2.imwrite(str(result_path), result)

    buf = io.BytesIO()
    Image.fromarray(result).save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg")


# ─── 图像增强（调色） ───

@app.post("/enhance")
async def enhance(req: EnhanceRequest):
    """调色/增强"""
    matches = list(UPLOAD_DIR.glob(f"{req.image_id}.*"))
    if not matches:
        raise HTTPException(404, "图片不存在")

    img = load_image(str(matches[0]))
    enh = get_enhance()

    # 如果指定了滤镜，先应用滤镜
    if req.filter:
        result = enh.apply_filter(img, req.filter)
    # 如果指定磨皮，应用中性灰磨皮
    elif req.skin_smooth:
        result = enh.skin_smooth(img)
    else:
        result = enh.adjust(
            img,
            brightness=req.brightness,
            contrast=req.contrast,
            saturation=req.saturation,
            warmth=req.warmth,
            sharpness=req.sharpness,
            denoise=req.denoise,
        )

    result_id = str(uuid.uuid4())[:8]
    result_path = OUTPUT_DIR / f"{result_id}.jpg"
    cv2.imwrite(str(result_path), result)

    buf = io.BytesIO()
    Image.fromarray(result).save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg")


# ─── 批量处理 ───

@app.post("/batch")
async def batch_process(req: BatchRequest):
    """批量处理多张图片"""
    results = []
    for img_id in req.image_ids:
        matches = list(UPLOAD_DIR.glob(f"{img_id}.*"))
        if not matches:
            results.append({"image_id": img_id, "status": "not_found"})
            continue

        try:
            img = load_image(str(matches[0]))

            if req.action == "enhance":
                enh = get_enhance()
                result = enh.adjust(img, **req.params)
            elif req.action == "auto_remove":
                seg = get_segmentation()
                inp = get_inpainting()
                masks = seg.auto_detect_people(img)
                if masks:
                    combined = np.zeros_like(masks[0])
                    for m in masks:
                        combined = np.maximum(combined, m)
                    result = inp.inpaint(img, combined)
                else:
                    result = img
            else:
                results.append({"image_id": img_id, "status": "unknown_action"})
                continue

            result_id = str(uuid.uuid4())[:8]
            result_path = OUTPUT_DIR / f"{result_id}.jpg"
            cv2.imwrite(str(result_path), result)
            results.append({"image_id": img_id, "result_id": result_id, "status": "ok"})

        except Exception as e:
            results.append({"image_id": img_id, "status": "error", "message": str(e)})

    return {"results": results, "total": len(req.image_ids)}


# ─── 下载结果 ───

@app.get("/download/{result_id}")
async def download_result(result_id: str):
    """下载处理结果"""
    matches = list(OUTPUT_DIR.glob(f"{result_id}.*"))
    if not matches:
        raise HTTPException(404, "结果不存在")

    path = matches[0]
    return StreamingResponse(
        open(path, "rb"),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"attachment; filename={result_id}.jpg"}
    )


# ──────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, reload=True)
