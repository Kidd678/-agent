import json
import os
import shutil
import tempfile
from pathlib import Path

import faiss
import numpy as np


class FaissToolStore:
    """FAISS 向量检索封装，用于工具粗排。"""

    def __init__(self):
        self._index: faiss.Index | None = None
        self._tool_ids: list[str] = []
        self._tool_id_to_meta: dict[str, dict] = {}
        self._tool_texts: dict[str, str] = {}

    def load(self, index_dir: Path, registry_path: Path):
        """从磁盘加载 FAISS 索引和工具元数据。"""
        # 加载索引（faiss C++ 不支持中文路径，先复制到临时目录）
        index_path = index_dir / "tools.index"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_index = os.path.join(tmp_dir, "tools.index")
            shutil.copy2(str(index_path), tmp_index)
            self._index = faiss.read_index(tmp_index)

        # 加载工具 ID 映射
        with open(index_dir / "tool_ids.json", "r", encoding="utf-8") as f:
            self._tool_ids = json.load(f)

        # 加载工具元数据
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        self._tool_id_to_meta = {t["id"]: t for t in registry["tools"]}

        # 加载工具复合文本（用于 reranker）
        with open(index_dir / "tool_texts.json", "r", encoding="utf-8") as f:
            self._tool_texts = json.load(f)

        print(f"FAISS index loaded: {self._index.ntotal} vectors")

    def search(self, query_vec: np.ndarray, top_k: int = 20) -> list[dict]:
        """返回 top-k 检索结果。"""
        query_vec = query_vec.astype(np.float32).reshape(1, -1)
        scores, indices = self._index.search(query_vec, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            tool_id = self._tool_ids[idx]
            results.append({
                "tool_id": tool_id,
                "score": float(score),
                "tool_meta": self._tool_id_to_meta.get(tool_id, {}),
            })
        return results

    def get_tool_text(self, tool_id: str) -> str:
        """获取工具的复合文本（用于 reranker 输入）。"""
        return self._tool_texts.get(tool_id, "")
