import json
import asyncio
import httpx
from pathlib import Path
from collections import Counter

# API 配置
API_KEY = "tp-czoo83bxmzsbe1ahu4c824mgvmh8rxcolh2j4d8swu6voxmi"
API_URL = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"

# 扩写提示词模板
AUGMENT_PROMPT = """你是一个数据标注专家。给定一条手机助手的用户输入示例和其意图类别，
请生成10条类似的用户输入，要求：
1. 口语化、自然，符合真实用户习惯
2. 不能与原句过于相似（避免简单改词）
3. 表达方式多样化，包含不同句式
4. 只输出用户输入，每行一条，不带编号

意图类别：{label}
示例输入：{example}

请生成10条类似输入："""

# 意图类别映射
LABEL_MAP = {
    "tool_call": "工具调用（查天气、设闹钟、打电话等）",
    "knowledge_qa": "知识问答（解释概念、百科类）",
    "chitchat": "闲聊（问候、情感表达等）",
    "system_op": "系统操作（打开WiFi、调亮度等）",
    "web_search": "网络搜索（查价格、搜新闻等）",
    "navigation": "导航出行（导航、查路线等）"
}


async def call_api(prompt: str) -> str:
    """调用 API 生成数据"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mimo-v2.5-pro",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def augment_single(item: dict, semaphore: asyncio.Semaphore) -> list[dict]:
    """扩写单条数据"""
    async with semaphore:
        label = item["output"]
        example = item["input"]
        label_desc = LABEL_MAP.get(label, label)

        prompt = AUGMENT_PROMPT.format(label=label_desc, example=example)

        try:
            result = await call_api(prompt)
            # 解析生成的文本，按行分割
            lines = [line.strip() for line in result.strip().split("\n") if line.strip()]

            # 过滤掉可能的编号前缀
            cleaned = []
            for line in lines:
                # 去掉可能的 "1. " 或 "- " 前缀
                if line and line[0].isdigit() and ". " in line[:4]:
                    line = line.split(". ", 1)[1]
                elif line.startswith("- "):
                    line = line[2:]
                if line:
                    cleaned.append(line)

            # 生成新的数据条目
            augmented = [{"input": text, "output": label} for text in cleaned[:10]]
            return augmented

        except Exception as e:
            print(f"扩写失败: {example}")
            print(f"错误类型: {type(e).__name__}: {str(e)}")
            return []


async def main():
    # 读取种子数据
    seed_path = Path("e:/1111/模拟agent/data/raw/seed_intents.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    print(f"读取种子数据: {len(seed_data)} 条")

    # 控制并发数，避免 API 限流
    semaphore = asyncio.Semaphore(3)

    # 批量扩写
    all_augmented = []
    tasks = [augment_single(item, semaphore) for item in seed_data]

    # 分批执行，每批 10 条
    batch_size = 10
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch)
        for result in results:
            all_augmented.extend(result)
        print(f"已完成 {min(i+batch_size, len(tasks))}/{len(tasks)} 条种子数据扩写")

    # 合并种子数据和扩写数据
    final_data = seed_data + all_augmented
    print(f"\n总数据量: {len(final_data)} 条 (种子 {len(seed_data)} + 扩写 {len(all_augmented)})")

    # 保存扩写后的数据
    output_path = Path("e:/1111/模拟agent/data/raw/augmented_intents.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"数据已保存到: {output_path}")

    # 统计各类别数量
    label_counts = Counter(item["output"] for item in final_data)
    print("\n各类别数据量:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count} 条")


if __name__ == "__main__":
    asyncio.run(main())
