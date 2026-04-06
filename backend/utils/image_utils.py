"""图像工具函数 - 修复中文路径支持"""

import numpy as np
import cv2
from pathlib import Path
from PIL import Image


def load_image(path: str) -> np.ndarray:
    """加载图像 (BGR) - 支持中文路径"""
    # cv2.imread 不支持非 ASCII 路径（Windows 常见问题）
    # 使用 np.fromfile + cv2.imdecode 绕过
    img_array = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法加载图像: {path}")
    return img


def save_image(path: str, image: np.ndarray):
    """保存图像 - 支持中文路径"""
    # cv2.imwrite 不支持非 ASCII 路径
    # 使用 cv2.imencode + Path.write_bytes 绕过
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        success, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    elif ext == ".png":
        success, buf = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    else:
        success, buf = cv2.imencode(ext, image)
    if not success:
        raise ValueError(f"图像编码失败: {path}")
    Path(path).write_bytes(buf.tobytes())


def image_to_bytes(image: np.ndarray, format: str = ".jpg", quality: int = 95) -> bytes:
    """图像转字节"""
    params = []
    if format in (".jpg", ".jpeg"):
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    elif format == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]

    success, buf = cv2.imencode(format, image, params)
    if not success:
        raise ValueError("图像编码失败")
    return buf.tobytes()


def imwrite_safe(path: str, image: np.ndarray, params=None) -> bool:
    """安全的 cv2.imwrite 替代，支持中文路径"""
    ext = Path(path).suffix.lower()
    if params is None:
        if ext in (".jpg", ".jpeg"):
            params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        elif ext == ".png":
            params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
    success, buf = cv2.imencode(ext, image, params or [])
    if success:
        Path(path).write_bytes(buf.tobytes())
    return success


def imread_safe(path: str, flags=cv2.IMREAD_COLOR) -> np.ndarray:
    """安全的 cv2.imread 替代，支持中文路径"""
    img_array = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(img_array, flags)


def resize_for_display(image: Image.Image, max_size: int = 2048) -> Image.Image:
    """等比缩放图像"""
    w, h = image.size
    if max(w, h) <= max_size:
        return image
    ratio = max_size / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    return image.resize(new_size, Image.LANCZOS)


def create_mask_from_points(
    points: list,
    width: int,
    height: int,
    brush_size: int = 20,
) -> np.ndarray:
    """从画笔点序列创建掩码"""
    mask = np.zeros((height, width), dtype=np.uint8)
    for i in range(len(points) - 1):
        x1, y1 = points[i]["x"], points[i]["y"]
        x2, y2 = points[i + 1]["x"], points[i + 1]["y"]
        cv2.line(mask, (x1, y1), (x2, y2), 255, brush_size)
    return mask


def compute_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """计算两个掩码的IoU"""
    m1 = mask1 > 127
    m2 = mask2 > 127
    intersection = np.logical_and(m1, m2).sum()
    union = np.logical_or(m1, m2).sum()
    if union == 0:
        return 0.0
    return float(intersection / union)


def create_comparison(original: np.ndarray, result: np.ndarray, axis: str = "horizontal") -> np.ndarray:
    """创建前后对比图"""
    if axis == "horizontal":
        h = min(original.shape[0], result.shape[0])
        w = min(original.shape[1], result.shape[1])
        left = cv2.resize(original, (w, h))
        right = cv2.resize(result, (w, h))
        center = w // 2
        left_half = left[:, :center]
        right_half = right[:, center:]
        comparison = np.hstack([left_half, right_half])
        cv2.line(comparison, (center, 0), (center, h), (255, 255, 255), 2)
    else:
        h = min(original.shape[0], result.shape[0])
        w = min(original.shape[1], result.shape[1])
        top = cv2.resize(original, (w, h))
        bottom = cv2.resize(result, (w, h))
        center = h // 2
        comparison = np.vstack([top[:center], bottom[center:]])
        cv2.line(comparison, (0, center), (w, center), (255, 255, 255), 2)

    return comparison
