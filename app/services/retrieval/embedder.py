import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"

import numpy as np
from sentence_transformers import SentenceTransformer


class ToolEmbedder:
    """BGE-M3 embedding wrapper (singleton)，基于 sentence-transformers。"""

    _instance: "ToolEmbedder | None" = None

    def __init__(self, model_name: str = "C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"):
        self._model = SentenceTransformer(model_name)

    @classmethod
    def get_instance(cls, model_name: str = "C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181") -> "ToolEmbedder":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def encode_query(self, query: str) -> np.ndarray:
        """编码单条用户 query，返回归一化向量。"""
        vec = self._model.encode([query], normalize_embeddings=True)
        return vec[0]

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        """批量编码工具描述文本，返回 (N, dim) 归一化向量矩阵。"""
        return self._model.encode(texts, normalize_embeddings=True)
