import os
from dataclasses import dataclass
from pathlib import Path

from app.services.intent.labels import (
    CLASSIFICATION_PROMPT,
    INTENT_LIST,
    INTENT_LABELS,
)

# 子服务地址（独立进程加载 LoRA 模型）
INTENT_SERVICE_URL = os.getenv("INTENT_SERVICE_URL", "http://127.0.0.1:8001")


@dataclass
class IntentResult:
    label: str
    confidence: float
    raw_output: str


class IntentClassifier:
    """意图分类器：通过 HTTP 调用独立的分类子服务。"""

    @classmethod
    async def predict(cls, query: str) -> IntentResult:
        import httpx
        from openai import AsyncOpenAI

        # 子服务兼容 OpenAI 接口，走 /v1/chat/completions
        # httpx 在 Windows 上连接 localhost 需要显式绑定 local_address，否则返回 502
        http_client = httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
        )
        client = AsyncOpenAI(
            api_key="unused",
            base_url=INTENT_SERVICE_URL + "/v1",
            http_client=http_client,
        )

        resp = await client.chat.completions.create(
            model="intent-classifier",
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=20,
            temperature=0,
        )

        raw = (resp.choices[0].message.content or "").strip()
        label = cls._parse_label(raw)
        return IntentResult(label=label, confidence=1.0, raw_output=raw)

    @staticmethod
    def _parse_label(raw: str) -> str:
        raw_lower = raw.lower().strip()
        for label in INTENT_LIST:
            if label in raw_lower:
                return label
        return "chitchat"
