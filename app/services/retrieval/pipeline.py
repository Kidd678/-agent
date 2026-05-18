import asyncio
from pathlib import Path


class RetrievalPipeline:
    """工具召回排序异步编排层。

    流程：BGE-M3 编码 → FAISS 粗排 Top-20 → bge-reranker 精排 Top-5
    """

    _embedder = None
    _store = None
    _reranker = None
    _initialized: bool = False

    @classmethod
    async def initialize(cls,
                         index_dir: Path = Path("data/tool_index"),
                         registry_path: Path = Path("tools/registry.json")):
        """启动时预加载所有模型和索引。"""
        if cls._initialized:
            return

        # 延迟导入，避免 FlagEmbedding 与 transformers 在启动时冲突导致 segfault
        from app.services.retrieval.embedder import ToolEmbedder
        from app.services.retrieval.faiss_store import FaissToolStore
        from app.services.retrieval.reranker import ToolReranker

        def _load():
            cls._embedder = ToolEmbedder.get_instance()
            cls._store = FaissToolStore()
            cls._store.load(index_dir, registry_path)
            cls._reranker = ToolReranker.get_instance()

        await asyncio.to_thread(_load)
        cls._initialized = True
        print("RetrievalPipeline initialized")

    @classmethod
    async def retrieve(cls, query: str, top_k: int = 5) -> list[dict]:
        """异步检索 top-k 工具。

        Args:
            query: 用户查询
            top_k: 最终返回的工具数量

        Returns:
            工具列表，每项为 registry.json 中的完整工具定义
        """
        if not cls._initialized:
            await cls.initialize()

        # 1. 编码 query（CPU/GPU 密集，放线程池）
        query_vec = await asyncio.to_thread(cls._embedder.encode_query, query)

        # 2. FAISS 粗排 Top-20
        candidates = await asyncio.to_thread(cls._store.search, query_vec, 20)

        # 3. 附加工具复合文本（供 reranker 使用）
        for cand in candidates:
            cand["tool_text"] = cls._store.get_tool_text(cand["tool_id"])

        # 4. Reranker 精排 Top-5
        results = await asyncio.to_thread(cls._reranker.rerank, query, candidates, top_k)

        # 5. 返回工具元数据列表
        return [r["tool_meta"] for r in results]
