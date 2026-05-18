"""离线构建工具 FAISS 向量索引。

用法：python scripts/build_index.py
输出：data/tool_index/tools.index, tool_ids.json, tool_texts.json
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import sys
import json
import shutil
import tempfile
from pathlib import Path

import faiss
import numpy as np

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.retrieval.embedder import ToolEmbedder

REGISTRY_PATH = PROJECT_ROOT / "tools" / "registry.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "tool_index"


def load_tools(registry_path: Path) -> list[dict]:
    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["tools"]


def build_composite_text(tool: dict) -> str:
    """构建工具的复合文本表示：名称 + 描述 + 示例。"""
    examples = "; ".join(tool.get("examples", []))
    return f"{tool['name']}。{tool['description']}。示例：{examples}"


def build_index():
    # 1. 加载工具注册表
    tools = load_tools(REGISTRY_PATH)
    print(f"Loaded {len(tools)} tools from {REGISTRY_PATH}")

    # 2. 构建复合文本
    tool_ids = [t["id"] for t in tools]
    texts = [build_composite_text(t) for t in tools]

    # 3. BGE-M3 编码
    print("Loading BGE-M3 model...")
    embedder = ToolEmbedder.get_instance()
    print("Encoding tool texts...")
    vectors = embedder.encode_documents(texts)
    print(f"Embedding shape: {vectors.shape}")

    # 4. 构建 FAISS 索引（IndexFlatIP，归一化向量 = 余弦相似度）
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors.astype(np.float32))
    print(f"FAISS index built: {index.ntotal} vectors, dim={dim}")

    # 5. 保存（faiss C++ 不支持中文路径，先写临时目录再移动）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_index = os.path.join(tmp_dir, "tools.index")
        faiss.write_index(index, tmp_index)
        shutil.move(tmp_index, str(OUTPUT_DIR / "tools.index"))

    with open(OUTPUT_DIR / "tool_ids.json", "w", encoding="utf-8") as f:
        json.dump(tool_ids, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DIR / "tool_texts.json", "w", encoding="utf-8") as f:
        json.dump(dict(zip(tool_ids, texts)), f, ensure_ascii=False, indent=2)

    print(f"Index saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    build_index()
