"""启动主服务，先预加载模型再启动 uvicorn。

关键：sentence-transformers 必须在 httpx 之前加载，否则 C 扩展冲突导致 segfault。
"""

# 1. 先加载检索模型（sentence-transformers / transformers）
from app.services.retrieval.embedder import ToolEmbedder
from app.services.retrieval.faiss_store import FaissToolStore
from app.services.retrieval.reranker import ToolReranker
from pathlib import Path

print("Preloading retrieval models...")
embedder = ToolEmbedder.get_instance()
store = FaissToolStore()
store.load(Path("data/tool_index"), Path("tools/registry.json"))
reranker = ToolReranker.get_instance()
print("Models preloaded.")

# 2. 设置到 RetrievalPipeline
from app.services.retrieval.pipeline import RetrievalPipeline
RetrievalPipeline._embedder = embedder
RetrievalPipeline._store = store
RetrievalPipeline._reranker = reranker
RetrievalPipeline._initialized = True

# 3. 现在可以安全导入 httpx/openai 相关模块
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
