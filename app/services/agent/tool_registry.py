from typing import Any


class ToolRegistry:
    """将召回到的工具转换为 OpenAI/Qwen Tool Call 格式。"""

    @staticmethod
    def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["id"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]
