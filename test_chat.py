import httpx
import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_one(client, name, query, session_id="s1", timeout=300):
    print(f"\n=== {name} ===")
    print(f"Query: {query}")
    try:
        resp = await client.post("http://127.0.0.1:8000/chat", json={
            "user_id": "test_user",
            "session_id": session_id,
            "query": query
        }, timeout=timeout)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Intent: {data['intent']}")
            print(f"Tools: {data['tools_used']}")
            print(f"Latency: {data['latency_ms']}ms")
            print(f"Response: {data['response'][:300]}")
        else:
            print(f"Error: {resp.text[:500]}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")

async def main():
    async with httpx.AsyncClient() as client:
        await test_one(client, "闲聊", "你好啊")
        await test_one(client, "知识问答", "什么是量子纠缠", session_id="s2")
        await test_one(client, "系统操作", "打开WiFi", session_id="s3")

if __name__ == "__main__":
    asyncio.run(main())
