import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class ToolReranker:
    """bge-reranker-v2-m3 交叉编码器封装（singleton），基于 transformers。"""

    _instance: "ToolReranker | None" = None

    def __init__(self, model_name: str = "C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3/snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"):
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            model_name, torch_dtype=torch.bfloat16
        )
        self._model.eval()
        if torch.cuda.is_available():
            self._model = self._model.cuda()

    @classmethod
    def get_instance(cls, model_name: str = "C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3/snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e") -> "ToolReranker":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def compute_score(self, pairs: list[list[str]]) -> list[float]:
        """计算 (query, passage) 对的相关性分数。"""
        inputs = self._tokenizer(
            pairs, padding=True, truncation=True, max_length=512, return_tensors="pt"
        )
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            scores = outputs.logits.squeeze(-1).float().cpu().tolist()

        if isinstance(scores, float):
            scores = [scores]
        return scores

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        """对 FAISS 粗排结果进行精排。"""
        if not candidates:
            return []

        pairs = [[query, c["tool_text"]] for c in candidates]
        scores = self.compute_score(pairs)

        for cand, score in zip(candidates, scores):
            cand["rerank_score"] = float(score)

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:top_k]
