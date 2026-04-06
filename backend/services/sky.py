"""
Sky Service - AI天空替换
基于天空分割 + 图像融合 + 颜色迁移
"""

import numpy as np
import cv2
from pathlib import Path


class SkyService:
    """天空替换服务"""

    # 内置天空素材（渐变色模拟）
    SKY_PRESETS = {
        "sunset": {
            "colors": [(25, 25, 112), (255, 140, 0), (255, 69, 0), (255, 200, 100)],
            "direction": "horizontal",
        },
        "blue": {
            "colors": [(135, 206, 235), (30, 144, 255), (0, 100, 200)],
            "direction": "vertical",
        },
        "cloudy": {
            "colors": [(200, 200, 210), (160, 160, 175), (130, 130, 145)],
            "direction": "vertical",
        },
        "starry": {
            "colors": [(10, 10, 30), (5, 5, 20), (0, 0, 10)],
            "direction": "vertical",
            "stars": True,
        },
        "golden_hour": {
            "colors": [(255, 180, 100), (255, 120, 50), (200, 80, 30)],
            "direction": "horizontal",
        },
        "overcast": {
            "colors": [(180, 180, 185), (150, 150, 155), (120, 120, 130)],
            "direction": "vertical",
        },
    }

    def __init__(self):
        self._sky_masks_dir = Path("assets/sky_masks")
        self._sky_images_dir = Path("assets/sky_images")
        self._sky_masks_dir.mkdir(parents=True, exist_ok=True)
        self._sky_images_dir.mkdir(parents=True, exist_ok=True)

    def replace(
        self,
        image: np.ndarray,
        sky_type: str = "sunset",
        sky_image: np.ndarray = None,
        blend: float = 0.7,
    ) -> np.ndarray:
        """
        替换天空

        Args:
            image: 输入图像
            sky_type: 天空类型 (sunset, blue, cloudy, starry, golden_hour, overcast)
            sky_image: 自定义天空图片（可选）
            blend: 融合强度 0-1

        Returns:
            替换后的图像
        """
        h, w = image.shape[:2]

        # 1. 分割天空
        sky_mask = self._detect_sky(image)
        if np.sum(sky_mask) == 0:
            return image  # 未检测到天空

        # 2. 生成/加载天空
        if sky_image is not None:
            sky = cv2.resize(sky_image, (w, h))
        else:
            sky = self._generate_sky(w, h, sky_type)

        # 3. 计算颜色匹配
        sky = self._color_transfer(image, sky, sky_mask)

        # 4. 融合
        result = self._blend(image, sky, sky_mask, blend)

        # 5. 添加大气透视效果
        result = self._add_atmosphere(result, sky_mask)

        return result

    def _detect_sky(self, image: np.ndarray) -> np.ndarray:
        """天空检测（多种策略融合）"""
        h, w = image.shape[:2]

        # 策略1: HSV颜色检测
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 蓝天
        mask_blue = cv2.inRange(hsv, np.array([90, 30, 80]), np.array([130, 255, 255]))
        # 白天/阴天
        mask_white = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 40, 255]))
        # 日落
        mask_sunset = cv2.inRange(hsv, np.array([0, 30, 100]), np.array([30, 255, 255]))
        # 夜空
        mask_night = cv2.inRange(hsv, np.array([100, 10, 10]), np.array([140, 100, 80]))

        mask_color = np.maximum(mask_blue, mask_white)
        mask_color = np.maximum(mask_color, mask_sunset)
        mask_color = np.maximum(mask_color, mask_night)

        # 策略2: 边缘密度（天空区域边缘少）
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = cv2.blur(edges.astype(np.float32), (50, 50))
        mask_edges = (edge_density < 10).astype(np.uint8) * 255

        # 策略3: 位置先验（天空通常在上部）
        position_weight = np.zeros((h, w), dtype=np.float32)
        for i in range(h):
            position_weight[i, :] = np.clip(1.0 - (i / h) * 1.8, 0, 1)

        # 融合策略
        mask_combined = (
            mask_color.astype(np.float32) * 0.5 +
            mask_edges.astype(np.float32) * 0.2 +
            position_weight * 255 * 0.3
        )
        mask = (mask_combined > 100).astype(np.uint8) * 255

        # 形态学清理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 保留在图像上半部分且连通的区域
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if n_labels > 1:
            best_label = 0
            best_score = 0
            for i in range(1, n_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                cy = stats[i, cv2.CC_STAT_TOP]
                # 上半部的大区域
                score = area * (1.0 - cy / h)
                if score > best_score:
                    best_score = score
                    best_label = i
            if best_label > 0:
                mask = ((labels == best_label) * 255).astype(np.uint8)

        # 边缘羽化
        mask = cv2.GaussianBlur(mask, (31, 31), 0)

        return mask

    def _generate_sky(self, w: int, h: int, sky_type: str) -> np.ndarray:
        """生成天空图像"""
        preset = self.SKY_PRESETS.get(sky_type, self.SKY_PRESETS["blue"])
        colors = preset["colors"]
        direction = preset["direction"]

        sky = np.zeros((h, w, 3), dtype=np.uint8)

        if direction == "vertical":
            for i in range(h):
                t = i / h
                idx = int(t * (len(colors) - 1))
                idx = min(idx, len(colors) - 2)
                local_t = t * (len(colors) - 1) - idx
                c = tuple(
                    int(colors[idx][j] * (1 - local_t) + colors[idx + 1][j] * local_t)
                    for j in range(3)
                )
                sky[i, :] = c
        else:  # horizontal
            for i in range(w):
                t = i / w
                idx = int(t * (len(colors) - 1))
                idx = min(idx, len(colors) - 2)
                local_t = t * (len(colors) - 1) - idx
                c = tuple(
                    int(colors[idx][j] * (1 - local_t) + colors[idx + 1][j] * local_t)
                    for j in range(3)
                )
                sky[:, i] = c

        # 添加星星
        if preset.get("stars"):
            rng = np.random.default_rng(42)
            n_stars = (w * h) // 500
            for _ in range(n_stars):
                x = rng.integers(0, w)
                y = rng.integers(0, h)
                brightness = int(rng.integers(180, 255))
                size = int(rng.choice([1, 1, 1, 2]))
                cv2.circle(sky, (int(x), int(y)), size, (brightness, brightness, brightness), -1)

        return sky

    def _color_transfer(self, source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """颜色迁移 - 使天空颜色与原图环境协调"""
        # 提取原图非天空区域的颜色统计
        inv_mask = cv2.bitwise_not(mask)
        source_region = cv2.bitwise_and(source, source, mask=inv_mask)

        if np.sum(inv_mask) == 0:
            return target

        # 计算原图均值和标准差
        source_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
        target_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype(np.float32)

        for i in range(3):
            src_mean = np.mean(source_lab[:, :, i][inv_mask > 0])
            src_std = np.std(source_lab[:, :, i][inv_mask > 0])
            tgt_mean = np.mean(target_lab[:, :, i])
            tgt_std = np.std(target_lab[:, :, i])

            if tgt_std > 0:
                target_lab[:, :, i] = (
                    (target_lab[:, :, i] - tgt_mean) * (src_std / tgt_std * 0.3 + 0.7) +
                    (tgt_mean * 0.5 + src_mean * 0.5)
                )

        result = cv2.cvtColor(target_lab.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
        return result

    def _blend(
        self,
        image: np.ndarray,
        sky: np.ndarray,
        mask: np.ndarray,
        strength: float,
    ) -> np.ndarray:
        """渐变融合"""
        mask_norm = mask.astype(np.float32) / 255.0 * strength
        mask_3ch = np.stack([mask_norm] * 3, axis=-1)

        result = image.astype(np.float32) * (1 - mask_3ch) + sky.astype(np.float32) * mask_3ch
        return result.clip(0, 255).astype(np.uint8)

    def _add_atmosphere(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """添加大气透视效果（远景雾化）"""
        # 简单版本：在天空区域底部轻微雾化
        h, w = image.shape[:2]

        # 找到天空区域的底部边缘
        mask_blur = mask.astype(np.float32) / 255.0

        # 创建垂直渐变（上部清晰，下部雾化）
        fog = np.zeros_like(image, dtype=np.float32)
        fog[:, :] = [220, 220, 220]  # 浅灰雾色

        fog_weight = mask_blur * 0.05  # 轻微雾化

        fog_3ch = np.stack([fog_weight] * 3, axis=-1)
        result = image.astype(np.float32) * (1 - fog_3ch) + fog * fog_3ch
        return result.clip(0, 255).astype(np.uint8)
