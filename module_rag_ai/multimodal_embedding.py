"""模块二：多模态特征提取。

职责：
- 加载 Chinese-CLIP（或兼容 CLIP）模型。
- 对商品图片、文本分别编码。
- 执行简单融合（加权求和），输出统一向量。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor


class ChineseCLIPEmbedder:
    """Chinese-CLIP 向量提取器。"""

    def __init__(
        self,
        model_name: str = "OFA-Sys/chinese-clip-vit-base-patch16",
        image_weight: float = 0.6,
        text_weight: float = 0.4,
    ):
        self.model_name = model_name
        self.image_weight = image_weight
        self.text_weight = text_weight
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    @torch.no_grad()
    def encode_text(self, text: str) -> np.ndarray:
        """编码单条文本为归一化向量。"""
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        text_features = self.model.get_text_features(**inputs)
        text_features = torch.nn.functional.normalize(text_features, dim=-1)
        return text_features[0].detach().cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def encode_image(self, image_path: str | Path) -> np.ndarray:
        """编码单张图片为归一化向量。"""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        image_features = self.model.get_image_features(**inputs)
        image_features = torch.nn.functional.normalize(image_features, dim=-1)
        return image_features[0].detach().cpu().numpy().astype(np.float32)

    def fuse(self, image_vec: np.ndarray, text_vec: np.ndarray) -> np.ndarray:
        """融合策略：加权求和 + L2 归一化。"""
        merged = self.image_weight * image_vec + self.text_weight * text_vec
        norm = np.linalg.norm(merged)
        if norm == 0:
            return merged.astype(np.float32)
        return (merged / norm).astype(np.float32)

    def encode_multimodal(self, image_path: str | Path, text: str) -> np.ndarray:
        image_vec = self.encode_image(image_path)
        text_vec = self.encode_text(text)
        return self.fuse(image_vec, text_vec)

    def batch_encode_text(self, texts: Iterable[str]) -> list[np.ndarray]:
        return [self.encode_text(t) for t in texts]
