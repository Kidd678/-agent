import httpx
import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with httpx.AsyncClient() as client:
        # Health check
        resp = await client.get("http://127.0.0.1:8001/health")
        print(f"Health: {resp.json()}")

        # Test predictions
        queries = [
            "帮我查一下明天北京的天气",
            "什么是量子纠缠",
            "你好啊",
            "打开WiFi",
            "搜索一下最新的iPhone价格",
            "导航去北京南站",
        ]

        for q in queries:
            resp = await client.post(
                "http://127.0.0.1:8001/v1/chat/completions",
                json={
                    "model": "intent-classifier",
                    "messages": [
                        {"role": "system", "content": "判断以下用户输入的意图类别，只输出类别名称。\n类别：tool_call / knowledge_qa / chitchat / system_op / web_search / navigation"},
                        {"role": "user", "content": q},
                    ],
                },
                timeout=30.0,
            )
            data = resp.json()
            label = data["choices"][0]["message"]["content"]
            print(f"  {q} -> {label}")

if __name__ == "__main__":
    asyncio.run(main())
