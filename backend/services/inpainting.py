"""
Inpainting Service - AI图像修复
基于 LaMa / Stable Diffusion Inpainting
支持：去路人、祛纹身、去胡渣、消除穿帮
"""

import numpy as np
import cv2
import torch
from PIL import Image


class InpaintingService:
    """图像修复服务，支持多种后端模型"""

    def __init__(self, model_type: str = "lama"):
        """
        Args:
            model_type: 模型类型
                - "lama": LaMa (轻量快速，适合大面积修复)
                - "sd": Stable Diffusion Inpainting (高质量，适合细节)
        """
        self.model_type = model_type
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None
        self._load_model()

    def _load_model(self):
        """延迟加载模型"""
        print(f"[Inpainting] 加载模型: {self.model_type} (device: {self.device})")

        if self.model_type == "lama":
            self._load_lama()
        elif self.model_type == "sd":
            self._load_sd()
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

    def _load_lama(self):
        """
        加载 LaMa 模型
        从 simple-lama-inpainting 包加载
        pip install simple-lama-inpainting
        """
        try:
            from simple_lama_inpainting import SimpleLama
            self._model = SimpleLama()
            print("[Inpainting] LaMa 模型加载完成")
        except ImportError:
            print("[Inpainting] simple-lama-inpainting 未安装，尝试从 HuggingFace 加载...")
            self._load_lama_hf()

    def _load_lama_hf(self):
        """从 HuggingFace 加载 LaMa"""
        try:
            from diffusers import AutoPipelineForInpainting
            self._model = AutoPipelineForInpainting.from_pretrained(
                "smartywu/big-lama",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device)
            print("[Inpainting] LaMa (HuggingFace) 加载完成")
        except Exception as e:
            print(f"[Inpainting] LaMa 加载失败: {e}")
            print("[Inpainting] 回退到 OpenCV inpainting (Telea)")
            self.model_type = "opencv"

    def _load_sd(self):
        """加载 Stable Diffusion Inpainting"""
        try:
            from diffusers import AutoPipelineForInpainting
            self._model = AutoPipelineForInpainting.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device)
            print("[Inpainting] SD Inpainting 加载完成")
        except Exception as e:
            print(f"[Inpainting] SD Inpainting 加载失败: {e}")
            self.model_type = "opencv"

    def inpaint(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        prompt: str = "",
        negative_prompt: str = "blurry, artifacts, low quality",
        strength: float = 0.8,
        guidance_scale: float = 7.5,
        num_steps: int = 30,
    ) -> np.ndarray:
        """
        执行图像修复

        Args:
            image: 输入图像 (H, W, 3) BGR
            mask: 修复掩码 (H, W) 0-255
            prompt: 文本提示 (SD模式)
            negative_prompt: 负面提示
            strength: 修复强度 0-1
            guidance_scale: CFG引导强度
            num_steps: 推理步数

        Returns:
            修复后的图像
        """
        if self.model_type == "lama":
            return self._inpaint_lama(image, mask)
        elif self.model_type == "sd":
            return self._inpaint_sd(
                image, mask, prompt, negative_prompt,
                strength, guidance_scale, num_steps
            )
        else:
            return self._inpaint_opencv(image, mask)

    def _inpaint_lama(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """LaMa 修复"""
        # 转为PIL
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        mask_pil = Image.fromarray(mask)

        # LaMa 推理
        result = self._model(img_pil, mask_pil)

        # 转回 numpy BGR
        result_np = np.array(result)
        return cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)

    def _inpaint_sd(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        prompt: str,
        negative_prompt: str,
        strength: float,
        guidance_scale: float,
        num_steps: int,
    ) -> np.ndarray:
        """Stable Diffusion 修复"""
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        mask_pil = Image.fromarray(mask)

        if not prompt:
            prompt = "high quality, detailed, seamless background, natural texture"

        result = self._model(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=img_pil,
            mask_image=mask_pil,
            strength=strength,
            guidance_scale=guidance_scale,
            num_inference_steps=num_steps,
        ).images[0]

        return cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)

    def _inpaint_opencv(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """OpenCV 兜底修复 (Telea算法)"""
        # 膨胀掩码边缘，使过渡更自然
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_dilated = cv2.dilate(mask, kernel, iterations=2)

        # Telea 修复
        result = cv2.inpaint(image, mask_dilated, inpaintRadius=7, flags=cv2.INPAINT_TELEA)

        # 额外高斯模糊使边缘更自然
        result = cv2.GaussianBlur(result, (3, 3), 0)

        return result

    def batch_inpaint(
        self,
        images: list[np.ndarray],
        masks: list[np.ndarray],
        **kwargs,
    ) -> list[np.ndarray]:
        """批量修复"""
        results = []
        for img, mask in zip(images, masks):
            result = self.inpaint(img, mask, **kwargs)
            results.append(result)
        return results
