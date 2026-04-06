"""
Enhance Service - 图像增强与调色
包含：调色、磨皮、AI追色、局部调整、滤镜预设
"""

import numpy as np
import cv2
from typing import Optional


class EnhanceService:
    """图像增强服务"""

    # ─── 内置滤镜预设 ───
    FILTER_PRESETS = {
        "青木胶片": {
            "brightness": 0.05, "contrast": 0.1, "saturation": -0.15,
            "warmth": -0.1, "tint_shift": [0, -10, 5], "vignette": 0.3,
        },
        "暖咖画报": {
            "brightness": 0.08, "contrast": 0.15, "saturation": 0.05,
            "warmth": 0.25, "tint_shift": [10, 15, -5], "vignette": 0.2,
        },
        "日系清新": {
            "brightness": 0.12, "contrast": -0.05, "saturation": -0.05,
            "warmth": -0.05, "tint_shift": [-5, 5, 10], "vignette": 0.0,
        },
        "复古胶片": {
            "brightness": -0.05, "contrast": 0.2, "saturation": -0.2,
            "warmth": 0.15, "tint_shift": [15, 10, -10], "vignette": 0.4,
        },
        "森系自然": {
            "brightness": 0.05, "contrast": 0.05, "saturation": 0.1,
            "warmth": 0.05, "tint_shift": [-10, 5, -5], "vignette": 0.1,
        },
        "赛博朋克": {
            "brightness": -0.1, "contrast": 0.3, "saturation": 0.4,
            "warmth": -0.2, "tint_shift": [-20, 10, 30], "vignette": 0.5,
        },
        "莫兰迪": {
            "brightness": 0.05, "contrast": -0.1, "saturation": -0.3,
            "warmth": 0.05, "tint_shift": [5, 5, 5], "vignette": 0.1,
        },
        "哈苏色彩": {
            "brightness": 0.03, "contrast": 0.08, "saturation": 0.05,
            "warmth": 0.02, "tint_shift": [2, 3, 5], "vignette": 0.15,
        },
        "徕卡色调": {
            "brightness": -0.03, "contrast": 0.18, "saturation": -0.1,
            "warmth": 0.08, "tint_shift": [8, -3, -5], "vignette": 0.35,
        },
    }

    def __init__(self):
        pass

    # ──────────────────────────────────────────
    # 基础调色
    # ──────────────────────────────────────────

    def adjust(
        self,
        image: np.ndarray,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
        warmth: float = 0.0,
        sharpness: float = 0.0,
        denoise: float = 0.0,
        highlights: float = 0.0,
        shadows: float = 0.0,
        whites: float = 0.0,
        blacks: float = 0.0,
        tint: float = 0.0,
        vibrance: float = 0.0,
        clarity: float = 0.0,
    ) -> np.ndarray:
        """
        全面色彩调整（Lightroom风格）

        参数范围: -1.0 ~ 1.0 (sharpness/denoise: 0~1)
        """
        result = image.astype(np.float32)

        # 亮度
        if brightness != 0:
            result = result + brightness * 255

        # 对比度
        if contrast != 0:
            factor = (1.0 + contrast)
            mean = np.mean(result, axis=(0, 1))
            result = (result - mean) * factor + mean

        # 高光 / 阴影
        if highlights != 0 or shadows != 0:
            gray = cv2.cvtColor(result.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
            # 高光区域 (>128)
            highlight_mask = np.clip((gray - 128) / 127, 0, 1)
            # 阴影区域 (<128)
            shadow_mask = np.clip((128 - gray) / 128, 0, 1)
            # 中间调
            mid_mask = 1 - highlight_mask - shadow_mask
            mid_mask = np.clip(mid_mask, 0, 1)

            for c in range(3):
                result[:, :, c] += highlight_mask * highlights * 80
                result[:, :, c] -= shadow_mask * shadows * 80  # shadows 为负=提亮暗部

        # 白色/黑色色阶
        if whites != 0:
            result = result + whites * 50
        if blacks != 0:
            result = result + blacks * 30

        # 饱和度
        if saturation != 0 or vibrance != 0:
            hsv = cv2.cvtColor(result.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            # 标准饱和度调整
            hsv[:, :, 1] = hsv[:, :, 1] * (1.0 + saturation)
            # Vibrance: 对低饱和区域增强更强
            if vibrance != 0:
                sat_norm = hsv[:, :, 1] / 255.0
                vibrance_mask = 1.0 - sat_norm  # 低饱和区域权重更高
                hsv[:, :, 1] += vibrance * vibrance_mask * 100
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

        # 色温
        if warmth != 0:
            result[:, :, 2] += warmth * 30  # Red
            result[:, :, 0] -= warmth * 20  # Blue

        # 色调偏移
        if tint != 0:
            result[:, :, 1] += tint * 20  # Green

        # 锐化
        if sharpness > 0:
            result = self._sharpen(result, sharpness)

        # 去噪
        if denoise > 0:
            result_uint8 = result.clip(0, 255).astype(np.uint8)
            h_param = int(denoise * 15) + 3
            result = cv2.fastNlMeansDenoisingColored(result_uint8, None, h_param, h_param, 7, 21).astype(np.float32)

        # 清晰度 (Clarity - 中频对比度增强)
        if clarity != 0:
            result = self._apply_clarity(result, clarity)

        return result.clip(0, 255).astype(np.uint8)

    def _sharpen(self, image: np.ndarray, amount: float) -> np.ndarray:
        """USM锐化"""
        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        sharpened = image + (image - blurred) * amount * 3
        return sharpened

    def _apply_clarity(self, image: np.ndarray, amount: float) -> np.ndarray:
        """清晰度调整（中频增强）"""
        # 高斯模糊获取低频
        low_freq = cv2.GaussianBlur(image, (0, 0), 15)
        # 中频 = 原图 - 低频
        mid_freq = image - low_freq
        # 增强中频
        result = image + mid_freq * amount * 2
        return result

    # ──────────────────────────────────────────
    # 滤镜预设
    # ──────────────────────────────────────────

    def apply_filter(self, image: np.ndarray, filter_name: str, intensity: float = 1.0) -> np.ndarray:
        """
        应用滤镜预设

        Args:
            image: 输入图像
            filter_name: 滤镜名称
            intensity: 滤镜强度 0-1
        """
        preset = self.FILTER_PRESETS.get(filter_name)
        if not preset:
            return image

        return self.adjust(
            image,
            brightness=preset.get("brightness", 0) * intensity,
            contrast=preset.get("contrast", 0) * intensity,
            saturation=preset.get("saturation", 0) * intensity,
            warmth=preset.get("warmth", 0) * intensity,
        )

    def get_filters(self) -> dict:
        """获取所有可用滤镜"""
        return {name: list(params.keys()) for name, params in self.FILTER_PRESETS.items()}

    # ──────────────────────────────────────────
    # AI 追色
    # ──────────────────────────────────────────

    def color_match(self, source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        AI追色 - 将参考图的色彩风格迁移到源图
        基于 Reinhard 颜色迁移 + LAB 空间匹配
        """
        # 转LAB空间
        src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
        ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)

        # 对每个通道做均值-方差匹配
        for i in range(3):
            src_mean, src_std = src_lab[:, :, i].mean(), src_lab[:, :, i].std()
            ref_mean, ref_std = ref_lab[:, :, i].mean(), ref_lab[:, :, i].std()

            if src_std > 0:
                src_lab[:, :, i] = (src_lab[:, :, i] - src_mean) * (ref_std / src_std) + ref_mean

        result = cv2.cvtColor(src_lab.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
        return result

    def color_match_advanced(self, source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        高级AI追色 - 分析光影、氛围与场景特征
        支持"换天造光"效果
        """
        # 1. 基础颜色匹配
        result = self.color_match(source, reference)

        # 2. 匹配光影分布
        src_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY).astype(np.float32)
        ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # 计算直方图并匹配
        result_gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # 使用直方图规定化
        for c in range(3):
            result[:, :, c] = self._match_histogram(
                result[:, :, c].astype(np.uint8),
                reference[:, :, c]
            )

        # 3. 匹配对比度
        src_contrast = np.std(src_gray)
        ref_contrast = np.std(ref_gray)
        if src_contrast > 0:
            contrast_ratio = ref_contrast / src_contrast
            contrast_ratio = np.clip(contrast_ratio, 0.5, 2.0)
            mean = np.mean(result.astype(np.float32))
            result = ((result.astype(np.float32) - mean) * contrast_ratio + mean).clip(0, 255).astype(np.uint8)

        return result

    def _match_histogram(self, source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """直方图匹配"""
        src_hist, _ = np.histogram(source.flatten(), 256, [0, 256])
        ref_hist, _ = np.histogram(reference.flatten(), 256, [0, 256])

        src_cdf = np.cumsum(src_hist).astype(np.float32)
        ref_cdf = np.cumsum(ref_hist).astype(np.float32)

        src_cdf /= src_cdf[-1]
        ref_cdf /= ref_cdf[-1]

        # 构建映射表
        mapping = np.zeros(256, dtype=np.uint8)
        for i in range(256):
            idx = np.argmin(np.abs(ref_cdf - src_cdf[i]))
            mapping[i] = idx

        return mapping[source]

    # ──────────────────────────────────────────
    # 局部调色
    # ──────────────────────────────────────────

    def local_adjust(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
        warmth: float = 0.0,
    ) -> np.ndarray:
        """
        基于掩码的局部调色

        Args:
            image: 输入图像
            mask: 区域掩码 (H, W) 0-255
            其他: 调色参数
        """
        # 对选区进行调色
        adjusted = self.adjust(
            image,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            warmth=warmth,
        )

        # 羽化掩码边界
        mask_blur = cv2.GaussianBlur(mask, (21, 21), 0).astype(np.float32) / 255.0
        mask_3ch = np.stack([mask_blur] * 3, axis=-1)

        # 融合
        result = image.astype(np.float32) * (1 - mask_3ch) + adjusted.astype(np.float32) * mask_3ch
        return result.clip(0, 255).astype(np.uint8)

    def radial_adjust(
        self,
        image: np.ndarray,
        center: tuple,
        radius: tuple,
        brightness: float = 0.0,
        contrast: float = 0.0,
        feather: float = 0.5,
    ) -> np.ndarray:
        """径向渐变调色"""
        h, w = image.shape[:2]
        cx, cy = center
        rx, ry = radius

        # 创建椭圆渐变
        Y, X = np.ogrid[:h, :w]
        dist = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
        mask = np.clip(1.0 - dist, 0, 1)

        # 羽化
        if feather > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), feather * 50)
            mask = np.clip(mask, 0, 1)

        mask_uint8 = (mask * 255).astype(np.uint8)
        return self.local_adjust(image, mask_uint8, brightness=brightness, contrast=contrast)

    def linear_adjust(
        self,
        image: np.ndarray,
        start: tuple,
        end: tuple,
        brightness: float = 0.0,
        contrast: float = 0.0,
        feather: float = 0.3,
    ) -> np.ndarray:
        """线性渐变调色"""
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)

        # 计算每个像素到渐变线的距离
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx ** 2 + dy ** 2)
        if length == 0:
            return image

        # 法线方向
        nx, ny = -dy / length, dx / length

        Y, X = np.mgrid[:h, :w]
        # 投影到渐变方向
        proj = (X - x1) * (dx / length) + (Y - y1) * (dy / length)
        mask = np.clip(proj / length, 0, 1)

        if feather > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), feather * 100)

        mask_uint8 = (mask * 255).astype(np.uint8)
        return self.local_adjust(image, mask_uint8, brightness=brightness, contrast=contrast)

    # ──────────────────────────────────────────
    # 补光
    # ──────────────────────────────────────────

    def relight(
        self,
        image: np.ndarray,
        brightness: float = 0.3,
        warmth: float = 0.1,
        direction: str = "natural",
    ) -> np.ndarray:
        """
        AI补光 - 智能光照调整

        direction: natural, dramatic, soft, backlight
        """
        h, w = image.shape[:2]

        if direction == "natural":
            # 自然补光：均匀提亮暗部
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
            # 暗部区域权重更高
            shadow_weight = np.clip(1.0 - gray * 2, 0, 1)
            result = image.astype(np.float32)
            for c in range(3):
                result[:, :, c] += shadow_weight * brightness * 150
            result = result.clip(0, 255).astype(np.uint8)

        elif direction == "dramatic":
            # 戏剧光：高对比度，伦勃朗光
            result = self.adjust(image, brightness=brightness * 0.5, contrast=0.3, clarity=0.4)

        elif direction == "soft":
            # 柔光：整体提亮，低对比
            result = self.adjust(image, brightness=brightness, contrast=-0.1, denoise=0.3)

        elif direction == "backlight":
            # 逆光补正：提亮主体，保持背景
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
            shadow_mask = np.clip(1.0 - gray * 1.5, 0, 1)
            # 提亮暗部
            result = image.astype(np.float32)
            for c in range(3):
                result[:, :, c] += shadow_mask * brightness * 200
            result = result.clip(0, 255).astype(np.uint8)
            # 去噪（暗部提亮后噪点明显）
            result = cv2.fastNlMeansDenoisingColored(result, None, 10, 10, 7, 21)
        else:
            result = image

        # 色温调整
        if warmth != 0:
            result = self.adjust(result, warmth=warmth)

        return result

    # ──────────────────────────────────────────
    # 皮肤美化（中性灰磨皮）
    # ──────────────────────────────────────────

    def skin_smooth(
        self,
        image: np.ndarray,
        skin_mask: Optional[np.ndarray] = None,
        strength: float = 0.5,
        preserve_texture: float = 0.6,
    ) -> np.ndarray:
        """
        中性灰磨皮 - 广告级皮肤美化

        通过分离光影层和颜色层，分别处理后重新组合，
        保留皮肤纹理的同时去除瑕疵。

        Args:
            image: 输入图像
            skin_mask: 皮肤区域掩码（可选，不提供则自动检测）
            strength: 磨皮强度 0-1
            preserve_texture: 纹理保留度 0-1
        """
        if skin_mask is None:
            skin_mask = self._detect_skin(image)

        # FIX: If no skin detected, apply smoothing to entire image for visible effect
        has_skin = cv2.countNonZero(skin_mask) > (image.shape[0] * image.shape[1] * 0.01)
        if not has_skin:
            # No skin found - apply to full image with gentler params
            full_mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
            skin_mask = full_mask

        result = image.copy()

        # 皮肤区域处理
        skin_region = cv2.bitwise_and(image, image, mask=skin_mask)

        # 1. 分离高频（纹理）和低频（颜色/光影）
        # 使用双边滤波保边平滑 - more aggressive params
        d = int(strength * 20) * 2 + 1
        sigma_color = strength * 120 + 60
        sigma_space = strength * 120 + 60
        smooth = cv2.bilateralFilter(skin_region, d, sigma_color, sigma_space)

        # 2. 提取纹理层
        texture = cv2.subtract(skin_region, smooth)

        # 3. 中性灰处理：消除色差和不均匀
        # 高斯模糊获取大尺度光影
        large_scale = cv2.GaussianBlur(smooth, (0, 0), 25)

        # 分离光影和颜色
        detail = cv2.subtract(smooth, large_scale)

        # 去除细节层中的瑕疵（小面积高对比区域）
        detail_blur = cv2.GaussianBlur(detail.astype(np.float32), (7, 7), 0)
        detail_cleaned = cv2.addWeighted(detail.astype(np.float32), preserve_texture,
                                          detail_blur, 1 - preserve_texture, 0)

        # 4. 重新组合
        smooth_cleaned = cv2.add(large_scale, detail_cleaned.clip(0, 255).astype(np.uint8))

        # 5. 混合纹理
        if preserve_texture > 0:
            # 保留部分原始高频纹理
            texture_preserved = cv2.addWeighted(
                smooth_cleaned, 1.0,
                texture, preserve_texture * 0.3,
                0
            )
        else:
            texture_preserved = smooth_cleaned

        # 6. 只在皮肤区域应用
        mask_3ch = np.stack([skin_mask / 255.0] * 3, axis=-1)
        result = image.astype(np.float32) * (1 - mask_3ch) + texture_preserved.astype(np.float32) * mask_3ch

        return result.clip(0, 255).astype(np.uint8)

    def _detect_skin(self, image: np.ndarray) -> np.ndarray:
        """肤色检测 - 支持多种肤色"""
        # YCrCb 空间检测 - broader range for various skin tones
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        lower = np.array([0, 125, 70])
        upper = np.array([255, 180, 135])
        mask1 = cv2.inRange(ycrcb, lower, upper)

        # HSV 空间辅助检测 - broader range
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower2 = np.array([0, 15, 50])
        upper2 = np.array([25, 255, 255])
        mask2 = cv2.inRange(hsv, lower2, upper2)
        # Also catch lighter skin (higher hue range)
        lower3 = np.array([160, 15, 50])
        upper3 = np.array([180, 255, 255])
        mask3 = cv2.inRange(hsv, lower3, upper3)

        mask = np.maximum(mask1, mask2)
        mask = np.maximum(mask, mask3)

        # 形态学清理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        return mask

    # ──────────────────────────────────────────
    # 牙齿美白
    # ──────────────────────────────────────────

    def teeth_whiten(self, image: np.ndarray, mask: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """牙齿美白"""
        # 提亮 + 降低黄色
        result = image.astype(np.float32)
        mask_norm = mask.astype(np.float32) / 255.0

        # 提亮
        for c in range(3):
            result[:, :, c] += mask_norm * strength * 80

        # 去黄（降低蓝色通道较少的区域的黄色）
        result[:, :, 2] -= mask_norm * strength * 20  # 降低红(黄色分量)
        result[:, :, 1] += mask_norm * strength * 5   # 微增绿

        return result.clip(0, 255).astype(np.uint8)
