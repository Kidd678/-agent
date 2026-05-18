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
    async def retrieve(cls, query: str, top_k: int = 5) -> tuple[list[dict], dict]:
        """异步检索 top-k 工具。

        Args:
            query: 用户查询
            top_k: 最终返回的工具数量

        Returns:
            (tools, debug_info) — 工具元数据列表 + 调试数据
        """
        if not cls._initialized:
            await cls.initialize()

        # 1. 编码 query（CPU/GPU 密集，放线程池）
        query_vec = await asyncio.to_thread(cls._embedder.encode_query, query)

        # 2. FAISS 粗排 Top-20
        candidates = await asyncio.to_thread(cls._store.search, query_vec, 20)

        # 保存 FAISS 粗排调试数据
        faiss_debug = [
            {"rank": i + 1, "tool_id": c["tool_id"], "score": round(c["score"], 4)}
            for i, c in enumerate(candidates)
        ]

        # 3. 附加工具复合文本（供 reranker 使用）
        for cand in candidates:
            cand["tool_text"] = cls._store.get_tool_text(cand["tool_id"])

        # 4. Reranker 精排 Top-5
        results = await asyncio.to_thread(cls._reranker.rerank, query, candidates, top_k)

        # 保存 Reranker 精排调试数据
        rerank_debug = [
            {"rank": i + 1, "tool_id": r["tool_id"], "rerank_score": round(r.get("rerank_score", 0), 4)}
            for i, r in enumerate(results)
        ]

        debug = {"faiss_top20": faiss_debug, "rerank_top5": rerank_debug}

        # 5. 返回工具元数据列表 + 调试数据
        return [r["tool_meta"] for r in results], debug
