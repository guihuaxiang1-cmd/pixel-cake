"""
Segmentation Service - AI语义分割
基于 SAM2 (Segment Anything Model 2) + MediaPipe ImageSegmenter
支持：交互式分割、自动人物检测、天空检测
"""

import os
import numpy as np
import cv2
import torch


class SegmentationService:
    """语义分割服务"""

    def __init__(self, model_type: str = "sam2"):
        """
        Args:
            model_type: 模型类型
                - "sam2": SAM2 (精度最高)
                - "mediapipe": MediaPipe (速度快)
        """
        self.model_type = model_type
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._sam = None
        self._mp_segmenter = None
        self._load_model()

    def _load_model(self):
        """加载分割模型"""
        if self.model_type == "sam2":
            self._load_sam2()
        elif self.model_type == "mediapipe":
            self._load_mediapipe()

    def _load_sam2(self):
        """加载 SAM2 模型"""
        try:
            # 尝试使用 sam2 包
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            # 使用 HuggingFace 预训练模型
            self._sam = SAM2ImagePredictor.from_pretrained(
                "facebook/sam2-hiera-large"
            )
            print("[Segmentation] SAM2 加载完成")
        except ImportError:
            try:
                # 回退到原始 SAM
                from segment_anything import sam_model_registry, SamPredictor
                sam = sam_model_registry["vit_h"](checkpoint="sam_vit_h.pth")
                sam.to(self.device)
                self._sam = SamPredictor(sam)
                print("[Segmentation] SAM (v1) 加载完成")
            except Exception as e:
                print(f"[Segmentation] SAM 加载失败: {e}")
                print("[Segmentation] 回退到 MediaPipe ImageSegmenter")
                self._load_mediapipe()

    def _load_mediapipe(self):
        """加载 MediaPipe ImageSegmenter (v0.10+ tasks API)"""
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            # Find model path relative to this file
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models", "selfie_segmenter.tflite"
            )

            if os.path.exists(model_path):
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = vision.ImageSegmenterOptions(
                    base_options=base_options,
                    output_category_mask=True
                )
                self._mp_segmenter = vision.ImageSegmenter.create_from_options(options)
                self.model_type = "mediapipe"
                print("[Segmentation] MediaPipe ImageSegmenter 加载完成")
            else:
                print(f"[Segmentation] MediaPipe 模型文件不存在: {model_path}")
                print("[Segmentation] 回退到传统CV方法")
                self.model_type = "cv"
        except Exception as e:
            print(f"[Segmentation] MediaPipe 加载失败: {e}")
            print("[Segmentation] 回退到传统CV方法")
            self.model_type = "cv"

    def predict(
        self,
        image: np.ndarray,
        points: list[tuple] = None,
        box: tuple = None,
    ) -> np.ndarray:
        """
        交互式分割预测

        Args:
            image: 输入图像 (H, W, 3) BGR
            points: 点列表 [(x, y, label), ...] label: 1=前景, 0=背景
            box: 边界框 (x1, y1, x2, y2)

        Returns:
            分割掩码 (H, W) 0-255
        """
        if self.model_type in ("sam2", "sam"):
            return self._predict_sam(image, points, box)
        else:
            return self._predict_cv(image, points, box)

    def _predict_sam(
        self,
        image: np.ndarray,
        points: list[tuple] = None,
        box: tuple = None,
    ) -> np.ndarray:
        """SAM 预测"""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self._sam.set_image(rgb)

        input_points = None
        input_labels = None
        if points:
            input_points = np.array([(p[0], p[1]) for p in points])
            input_labels = np.array([p[2] for p in points])

        input_box = None
        if box:
            input_box = np.array(box)

        masks, scores, _ = self._sam.predict(
            point_coords=input_points,
            point_labels=input_labels,
            box=input_box,
            multimask_output=True,
        )

        # 选择分数最高的掩码
        best_idx = np.argmax(scores)
        mask = masks[best_idx]

        return (mask * 255).astype(np.uint8)

    def _predict_cv(
        self,
        image: np.ndarray,
        points: list[tuple] = None,
        box: tuple = None,
    ) -> np.ndarray:
        """传统CV方法兜底"""
        if points:
            return self._grabcut_predict(image, points, box)
        elif box:
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            x1, y1, x2, y2 = map(int, box)
            mask[y1:y2, x1:x2] = 255
            return mask
        else:
            return np.zeros(image.shape[:2], dtype=np.uint8)

    def _grabcut_predict(
        self,
        image: np.ndarray,
        points: list[tuple],
        box: tuple = None,
    ) -> np.ndarray:
        """GrabCut 分割"""
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        # 根据点推断大致区域
        fg_points = [p for p in points if p[2] == 1]
        if fg_points:
            xs = [p[0] for p in fg_points]
            ys = [p[1] for p in fg_points]
            margin = 50
            rect = (
                max(0, min(xs) - margin),
                max(0, min(ys) - margin),
                min(image.shape[1], max(xs) - min(xs) + 2 * margin),
                min(image.shape[0], max(ys) - min(ys) + 2 * margin),
            )
        elif box:
            rect = (
                box[0], box[1],
                box[2] - box[0], box[3] - box[1]
            )
        else:
            h, w = image.shape[:2]
            rect = (w // 4, h // 4, w // 2, h // 2)

        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

        result_mask = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)

        return result_mask

    def auto_detect_people(self, image: np.ndarray) -> list[np.ndarray]:
        """
        自动检测画面中的所有人物

        Returns:
            掩码列表，每个掩码对应一个人物
        """
        if self.model_type == "mediapipe":
            return self._detect_people_mediapipe(image)
        else:
            return self._detect_people_cv(image)

    def _detect_people_mediapipe(self, image: np.ndarray) -> list[np.ndarray]:
        """MediaPipe ImageSegmenter 人物分割"""
        import mediapipe as mp

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._mp_segmenter.segment(mp_image)
        category_mask = result.category_mask.numpy_view()

        # category_mask: 0=background, 1=person (selfie segmenter)
        # Some versions use 255 for person
        person_mask = (category_mask > 0).astype(np.uint8) * 255

        if np.count_nonzero(person_mask) > 0:
            # Morphological cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            person_mask = cv2.morphologyEx(person_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            person_mask = cv2.morphologyEx(person_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            return self._split_connected_regions(person_mask)
        return []

    def _detect_people_cv(self, image: np.ndarray) -> list[np.ndarray]:
        """传统CV方法检测人物（基于HOG+SVM）"""
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # 多尺度检测
        rects, weights = hog.detectMultiScale(
            image, winStride=(4, 4), padding=(8, 8), scale=1.05
        )

        masks = []
        for (x, y, w, h) in rects:
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            # 稍微扩展检测框
            x1 = max(0, x - w // 10)
            y1 = max(0, y - h // 10)
            x2 = min(image.shape[1], x + w + w // 10)
            y2 = min(image.shape[0], y + h + h // 5)
            mask[y1:y2, x1:x2] = 255

            # 用GrabCut精细化
            refined = self._refine_with_grabcut(image, mask)
            masks.append(refined)

        return masks

    def _refine_with_grabcut(self, image: np.ndarray, rough_mask: np.ndarray) -> np.ndarray:
        """用GrabCut精细化粗掩码"""
        mask = np.where(rough_mask > 0, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            cv2.grabCut(image, mask, None, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_MASK)
            result = np.where(
                (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
            ).astype(np.uint8)
        except cv2.error:
            result = rough_mask

        # 形态学清理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel, iterations=2)
        result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel, iterations=1)

        return result

    def auto_detect_sky(self, image: np.ndarray) -> list[np.ndarray]:
        """自动检测天空区域"""
        h, w = image.shape[:2]

        # 转HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 蓝色天空检测
        lower_blue = np.array([90, 30, 80])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

        # 白色/灰色天空（阴天）
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 40, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)

        # 橙色天空（日落）
        lower_orange = np.array([5, 50, 80])
        upper_orange = np.array([25, 255, 255])
        mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)

        # 合并
        mask = np.maximum(mask_blue, mask_white)
        mask = np.maximum(mask, mask_orange)

        # 天空通常在画面上部
        # 创建上部权重图
        weight = np.zeros((h, w), dtype=np.float32)
        for i in range(h):
            weight[i, :] = max(0, 1.0 - (i / h) * 1.5)
        mask = (mask.astype(np.float32) * weight).astype(np.uint8)

        # 形态学清理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 取最大连通区域
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if n_labels > 1:
            largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            mask = ((labels == largest) * 255).astype(np.uint8)

        if np.sum(mask) > 0:
            return [mask]
        return []

    def auto_detect_all(self, image: np.ndarray) -> list[np.ndarray]:
        """检测所有显著物体"""
        # 简单方法：GrabCut 全图分割
        h, w = image.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        rect = (10, 10, w - 20, h - 20)
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

        fg_mask = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)

        return self._split_connected_regions(fg_mask, min_area=5000)

    def _split_connected_regions(self, mask: np.ndarray, min_area: int = 1000) -> list[np.ndarray]:
        """将掩码拆分为独立连通区域"""
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        regions = []
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                region = ((labels == i) * 255).astype(np.uint8)

                # 形态学清理
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, kernel, iterations=2)
                regions.append(region)
        return regions
