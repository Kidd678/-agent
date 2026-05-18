import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.services.agent.tool_registry import ToolRegistry

# 工具实现注册表：tool_id -> 实现函数
_TOOL_IMPLS: dict[str, Any] = {}


def register_tool(tool_id: str):
    """装饰器，注册工具实现。"""
    def decorator(func):
        _TOOL_IMPLS[tool_id] = func
        return func
    return decorator


# ---- Mock 工具实现（后续替换为真实逻辑） ----

@register_tool("weather_query")
async def _weather(city: str, date: str = "today") -> str:
    return f"[Mock] {city} {date} 天气：晴，25°C"


@register_tool("alarm_set")
async def _alarm(time: str, label: str = "") -> str:
    return f"[Mock] 闹钟已设置：{time} {label}"


# 未注册工具的兜底
async def _default_impl(tool_name: str, arguments: dict) -> str:
    return f"[Mock] {tool_name} 执行结果：{arguments}"


class MCPExecutor:
    """MCP Tool Call 执行器：LLM 决策 → 并发执行工具 → 聚合结果。"""

    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client or AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL

    async def run(self, query: str, tools: list[dict], history: list[dict] | None = None) -> dict:
        """
        Args:
            query: 用户输入
            tools: 工具列表（registry.json 格式）
            history: 历史对话

        Returns:
            {"response": str, "tools_used": list[str]}
        """
        history = history or []
        openai_tools = ToolRegistry.to_openai_tools(tools)

        # 第一次调用：让 LLM 决定用哪些工具
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=history + [{"role": "user", "content": query}],
            tools=openai_tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return {"response": message.content or "", "tools_used": []}

        # 并发执行所有工具调用
        tool_results = await asyncio.gather(*[
            self._execute_tool(tc.function.name, tc.function.arguments)
            for tc in message.tool_calls
        ])

        # 将工具结果追加到 messages
        tool_messages = [
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            }
            for tc, result in zip(message.tool_calls, tool_results)
        ]

        # 第二次调用：让 LLM 根据工具结果生成最终回复
        final_response = await self.client.chat.completions.create(
            model=self.model,
            messages=history + [
                {"role": "user", "content": query},
                message,
                *tool_messages,
            ],
        )

        return {
            "response": final_response.choices[0].message.content or "",
            "tools_used": [tc.function.name for tc in message.tool_calls],
        }

    async def _execute_tool(self, tool_name: str, arguments: str) -> Any:
        args = json.loads(arguments)
        impl = _TOOL_IMPLS.get(tool_name)
        if impl:
            return await impl(**args)
        return await _default_impl(tool_name, args)
