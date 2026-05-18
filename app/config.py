import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# LLM API 配置（MiMo，兼容 OpenAI 接口）
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "tp-czoo83bxmzsbe1ahu4c824mgvmh8rxcolh2j4d8swu6voxmi")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "mimo-v2.5-pro")

# 本地意图分类模型路径
LOCAL_INTENT_MODEL_PATH: str = os.getenv(
    "LOCAL_INTENT_MODEL_PATH",
    str(Path(__file__).resolve().parent.parent / "lora" / "model" / "lora"),
)
