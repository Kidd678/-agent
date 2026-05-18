from __future__ import annotations

from pydantic import BaseModel


class DebugInfo(BaseModel):
    faiss_top20: list[dict] = []
    rerank_top5: list[dict] = []
    llm_tool_calls: list[dict] = []
    tool_results: list[dict] = []
    llm_final_response: str = ""


class ChatResponse(BaseModel):
    response: str
    intent: str
    tools_used: list[str]
    latency_ms: float
    debug: DebugInfo | None = None
