import json
import random
from pathlib import Path
from collections import Counter

# 配置
INPUT_PATH = Path("e:/1111/模拟agent/data/raw/augmented_intents.json")
OUTPUT_DIR = Path("e:/1111/模拟agent/data/processed")
SEED = 42

# Alpaca 格式模板
INSTRUCTION = "判断以下用户输入的意图类别，只输出类别名称。\n类别：tool_call / knowledge_qa / chitchat / system_op / web_search / navigation"


def convert_to_alpaca(data: list[dict]) -> list[dict]:
    """转换为 Alpaca 格式"""
    alpaca_data = []
    for item in data:
        alpaca_data.append({
            "instruction": INSTRUCTION,
            "input": item["input"],
            "output": item["output"]
        })
    return alpaca_data


def split_dataset(data: list[dict], train_ratio=0.8, dev_ratio=0.1, test_ratio=0.1):
    """划分数据集"""
    random.seed(SEED)
    random.shuffle(data)

    n = len(data)
    train_end = int(n * train_ratio)
    dev_end = train_end + int(n * dev_ratio)

    train_data = data[:train_end]
    dev_data = data[train_end:dev_end]
    test_data = data[dev_end:]

    return train_data, dev_data, test_data


def print_stats(data: list[dict], name: str):
    """打印数据集统计"""
    label_counts = Counter(item["output"] for item in data)
    print(f"\n{name} 数据集: {len(data)} 条")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count} 条")


def main():
    # 读取原始数据
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"原始数据量: {len(raw_data)} 条")

    # 转换为 Alpaca 格式
    alpaca_data = convert_to_alpaca(raw_data)
    print(f"转换后数据量: {len(alpaca_data)} 条")

    # 划分数据集
    train_data, dev_data, test_data = split_dataset(alpaca_data)

    # 打印统计
    print_stats(train_data, "Train")
    print_stats(dev_data, "Dev")
    print_stats(test_data, "Test")

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 保存数据集
    for name, dataset in [("train", train_data), ("dev", dev_data), ("test", test_data)]:
        output_path = OUTPUT_DIR / f"{name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"已保存: {output_path}")

    # 保存完整数据集（用于 LLaMA-Factory 注册）
    full_path = OUTPUT_DIR / "intent_full.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)
    print(f"已保存完整数据集: {full_path}")

    print("\n数据准备完成!")


if __name__ == "__main__":
    main()
