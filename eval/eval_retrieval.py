"""工具召回排序评测脚本。

用法：
    python eval/eval_retrieval.py                  # 完整评测（BM25 + FAISS + Reranker）
    python eval/eval_retrieval.py --mode faiss      # 仅 FAISS 评测
    python eval/eval_retrieval.py --mode full       # FAISS + Reranker 评测
    python eval/eval_retrieval.py --mode bm25       # 仅 BM25 baseline
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import sys
import json
import argparse
import asyncio
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATA_PATH = PROJECT_ROOT / "data" / "tool_test" / "retrieval_testset.json"
REGISTRY_PATH = PROJECT_ROOT / "tools" / "registry.json"


# ─── 指标计算 ─────────────────────────────────────────────

def recall_at_k(retrieved_ids: list[str], positive_ids: list[str], k: int) -> float:
    """Top-k 中是否包含正例。"""
    top_k = retrieved_ids[:k]
    return float(any(r in positive_ids for r in top_k))


def mrr(retrieved_ids: list[str], positive_ids: list[str]) -> float:
    """第一个正例的倒数排名。"""
    for i, r in enumerate(retrieved_ids):
        if r in positive_ids:
            return 1.0 / (i + 1)
    return 0.0


# ─── BM25 Baseline ────────────────────────────────────────

def build_bm25_index():
    """构建 BM25 索引。"""
    import jieba
    from rank_bm25 import BM25Okapi

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        tools = json.load(f)["tools"]

    tool_ids = [t["id"] for t in tools]
    # 复合文本与向量检索一致
    corpus = [f"{t['name']} {t['description']} {' '.join(t.get('examples', []))}" for t in tools]
    tokenized = [list(jieba.cut(doc)) for doc in corpus]

    bm25 = BM25Okapi(tokenized)
    return bm25, tool_ids


def bm25_search(query: str, bm25, tool_ids: list[str], top_k: int = 20) -> list[str]:
    """BM25 检索。"""
    import jieba
    tokens = list(jieba.cut(query))
    scores = bm25.get_scores(tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [tool_ids[i] for i in top_indices]


def evaluate_bm25(test_cases: list[dict], top_ks: list[int]) -> dict:
    """BM25 baseline 评测。"""
    print("Building BM25 index...")
    bm25, tool_ids = build_bm25_index()

    results = {f"Recall@{k}": 0.0 for k in top_ks}
    results["MRR"] = 0.0

    for case in test_cases:
        retrieved = bm25_search(case["query"], bm25, tool_ids, max(top_ks))
        positives = case["positive_tool_ids"]

        for k in top_ks:
            results[f"Recall@{k}"] += recall_at_k(retrieved, positives, k)
        results["MRR"] += mrr(retrieved, positives)

    n = len(test_cases)
    for key in results:
        results[key] /= n

    return results


# ─── FAISS 评测 ───────────────────────────────────────────

async def evaluate_faiss(test_cases: list[dict], top_ks: list[int]) -> dict:
    """FAISS 向量检索评测。"""
    from app.services.retrieval.pipeline import RetrievalPipeline

    await RetrievalPipeline.initialize()
    store = RetrievalPipeline._store
    embedder = RetrievalPipeline._embedder

    results = {f"Recall@{k}": 0.0 for k in top_ks}
    results["MRR"] = 0.0

    for case in test_cases:
        query_vec = await asyncio.to_thread(embedder.encode_query, case["query"])
        candidates = await asyncio.to_thread(store.search, query_vec, max(top_ks))
        retrieved = [c["tool_id"] for c in candidates]
        positives = case["positive_tool_ids"]

        for k in top_ks:
            results[f"Recall@{k}"] += recall_at_k(retrieved, positives, k)
        results["MRR"] += mrr(retrieved, positives)

    n = len(test_cases)
    for key in results:
        results[key] /= n

    return results


# ─── FAISS + Reranker 评测 ────────────────────────────────

async def evaluate_full(test_cases: list[dict], top_ks: list[int]) -> dict:
    """FAISS + Reranker 完整管线评测。"""
    from app.services.retrieval.pipeline import RetrievalPipeline

    await RetrievalPipeline.initialize()

    results = {f"Recall@{k}": 0.0 for k in top_ks}
    results["MRR"] = 0.0

    for case in test_cases:
        tools = await RetrievalPipeline.retrieve(case["query"], top_k=max(top_ks))
        retrieved = [t["id"] for t in tools]
        positives = case["positive_tool_ids"]

        for k in top_ks:
            results[f"Recall@{k}"] += recall_at_k(retrieved, positives, k)
        results["MRR"] += mrr(retrieved, positives)

    n = len(test_cases)
    for key in results:
        results[key] /= n

    return results


# ─── 主函数 ───────────────────────────────────────────────

def print_table(title: str, results: dict):
    print(f"\n{'='*40}")
    print(f"  {title}")
    print(f"{'='*40}")
    for metric, value in results.items():
        print(f"  {metric:<12} {value:.4f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="工具召回排序评测")
    parser.add_argument("--mode", choices=["bm25", "faiss", "full", "all"], default="all",
                        help="评测模式: bm25 / faiss / full / all")
    args = parser.parse_args()

    # 加载测试集
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)
    print(f"Loaded {len(test_cases)} test cases")

    top_ks = [1, 3, 5]

    if args.mode in ("bm25", "all"):
        bm25_results = evaluate_bm25(test_cases, top_ks)
        print_table("BM25 Baseline", bm25_results)

    if args.mode in ("faiss", "all"):
        faiss_results = asyncio.run(evaluate_faiss(test_cases, top_ks))
        print_table("FAISS (BGE-M3)", faiss_results)

    if args.mode in ("full", "all"):
        full_results = asyncio.run(evaluate_full(test_cases, top_ks))
        print_table("FAISS + Reranker", full_results)

    # 汇总对比表
    if args.mode == "all":
        print("="*60)
        print("  对比汇总")
        print("="*60)
        print(f"  {'方法':<25} {'Recall@1':<10} {'Recall@3':<10} {'Recall@5':<10} {'MRR':<10}")
        print(f"  {'-'*55}")
        for name, res in [("BM25", bm25_results), ("FAISS (BGE-M3)", faiss_results), ("FAISS+Reranker", full_results)]:
            print(f"  {name:<25} {res['Recall@1']:<10.4f} {res['Recall@3']:<10.4f} {res['Recall@5']:<10.4f} {res['MRR']:<10.4f}")
        print()


if __name__ == "__main__":
    main()
