#!/bin/bash
# AutoDL 训练环境配置脚本

# 复制数据集到 LLaMA-Factory 目录
LLAMAFATORY_DATA_DIR="/root/miniconda3/lib/python3.10/site-packages/llamafactory/data"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "项目目录: $PROJECT_DIR"
echo "LLaMA-Factory 数据目录: $LLAMAFATORY_DATA_DIR"

# 复制数据集文件
cp "$PROJECT_DIR/data/processed/train.json" "$LLAMAFATORY_DATA_DIR/"
cp "$PROJECT_DIR/data/processed/dev.json" "$LLAMAFATORY_DATA_DIR/"
cp "$PROJECT_DIR/data/processed/test.json" "$LLAMAFATORY_DATA_DIR/"
cp "$PROJECT_DIR/data/processed/intent_full.json" "$LLAMAFATORY_DATA_DIR/"

# 复制数据集注册文件
cp "$PROJECT_DIR/training/llamafactory/dataset_info.json" "$LLAMAFATORY_DATA_DIR/dataset_info.json"

echo "数据集复制完成!"
echo ""
echo "数据集统计:"
echo "  train.json: $(cat "$PROJECT_DIR/data/processed/train.json" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))") 条"
echo "  dev.json: $(cat "$PROJECT_DIR/data/processed/dev.json" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))") 条"
echo "  test.json: $(cat "$PROJECT_DIR/data/processed/test.json" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))") 条"
echo ""
echo "现在可以开始训练:"
echo "  llamafactory-cli train training/llamafactory/qwen7b_lora_sft.yaml"
