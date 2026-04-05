"""图像工具函数"""

import numpy as np
import cv2
from PIL import Image


def load_image(path: str) -> np.ndarray:
    """加载图像 (BGR)"""
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"无法加载图像: {path}")
    return img


def save_image(path: str, image: np.ndarray):
    """保存图像"""
    cv2.imwrite(path, image)


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
        # 添加分隔线
        center = w // 2
        left_half = left[:, :center]
        right_half = right[:, center:]
        comparison = np.hstack([left_half, right_half])
        # 画分隔线
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
