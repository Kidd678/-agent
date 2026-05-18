from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.intent.classifier import IntentClassifier, IntentResult
from app.services.memory.session_store import SessionStore


@dataclass
class RouteResult:
    response: str
    tools_used: list[str]


class Router:
    """意图 → 链路映射。"""

    _executor = None

    @classmethod
    def _get_executor(cls):
        if cls._executor is None:
            from app.services.agent.mcp_executor import MCPExecutor
            cls._executor = MCPExecutor()
        return cls._executor

    @classmethod
    async def dispatch(
        cls,
        query: str,
        intent: IntentResult,
        history: list[dict[str, str]] | None = None,
    ) -> RouteResult:
        label = intent.label

        if label == "tool_call":
            return await cls._handle_tool_call(query, history)
        elif label == "knowledge_qa":
            return await cls._handle_knowledge_qa(query, history)
        elif label == "chitchat":
            return await cls._handle_chitchat(query)
        elif label == "system_op":
            return await cls._handle_tool_call(query, history)
        elif label == "web_search":
            return await cls._handle_tool_call(query, history)
        elif label == "navigation":
            return await cls._handle_tool_call(query, history)
        else:
            return await cls._handle_chitchat(query)

    @classmethod
    async def _handle_tool_call(
        cls, query: str, history: list[dict[str, str]] | None
    ) -> RouteResult:
        from app.services.retrieval.pipeline import RetrievalPipeline
        tools = await RetrievalPipeline.retrieve(query, top_k=5)
        from app.services.agent.mcp_executor import MCPExecutor
        executor = cls._get_executor()
        result = await executor.run(query=query, tools=tools, history=history)
        return RouteResult(response=result["response"], tools_used=result["tools_used"])

    @classmethod
    async def _handle_knowledge_qa(
        cls, query: str, history: list[dict[str, str]] | None
    ) -> RouteResult:
        from openai import AsyncOpenAI
        from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

        client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        messages = (history or []) + [{"role": "user", "content": query}]
        resp = await client.chat.completions.create(model=LLM_MODEL, messages=messages)
        return RouteResult(response=resp.choices[0].message.content or "", tools_used=[])

    @classmethod
    async def _handle_chitchat(cls, query: str) -> RouteResult:
        from openai import AsyncOpenAI
        from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

        client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个友好的手机助手，用简短自然的方式回复。"},
                {"role": "user", "content": query},
            ],
        )
        return RouteResult(response=resp.choices[0].message.content or "", tools_used=[])
