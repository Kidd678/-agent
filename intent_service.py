"""意图分类独立子服务。

独立进程运行，加载 LoRA 微调模型，暴露 OpenAI 兼容接口。
主服务通过 HTTP 调用本服务，避免 torch/transformers 与 FlagEmbedding 的进程冲突。

启动方式：
    python intent_service.py                    # 默认 8001 端口
    python intent_service.py --port 8001        # 指定端口
"""

import argparse
import os
import time
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

# ── 配置 ──────────────────────────────────────────────────

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

MODEL_PATH = Path(
    os.getenv("LOCAL_INTENT_MODEL_PATH",
              str(Path(__file__).resolve().parent / "lora" / "model" / "lora"))
)

CLASSIFICATION_PROMPT = (
    "判断以下用户输入的意图类别，只输出类别名称。\n"
    "类别：tool_call / knowledge_qa / chitchat / system_op / web_search / navigation"
)

INTENT_LIST = ["tool_call", "knowledge_qa", "chitchat", "system_op", "web_search", "navigation"]

# ── FastAPI App ───────────────────────────────────────────

app = FastAPI(title="Intent Classification Service")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "intent-classifier"
    messages: list[ChatMessage]
    max_tokens: int = 20
    temperature: float = 0


class ChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str = "intent-classifier"
    choices: list[Choice]
    usage: Usage


# ── 模型加载 ──────────────────────────────────────────────

_tokenizer = None
_model = None


def load_model():
    global _tokenizer, _model
    if _model is not None:
        return

    model_dir = str(MODEL_PATH)
    print(f"Loading intent classifier from {model_dir} ...")

    _tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    _model.eval()
    print("Intent classifier loaded.")


def predict_sync(query: str) -> tuple[str, float, str]:
    """同步推理，返回 (label, confidence, raw_output)。"""
    load_model()

    messages = [
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": query},
    ]
    text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer(text, return_tensors="pt").to(_model.device)

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=False,
            pad_token_id=_tokenizer.pad_token_id,
            return_dict_in_generate=True,
            output_scores=True,
        )

    new_tokens = outputs.sequences[0][inputs["input_ids"].shape[-1]:]
    raw = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    confidence = 1.0
    if outputs.scores:
        first_token_logits = outputs.scores[0][0]
        probs = torch.softmax(first_token_logits, dim=-1)
        confidence = probs.max().item()

    # 解析标签
    label = "chitchat"
    raw_lower = raw.lower().strip()
    for l in INTENT_LIST:
        if l in raw_lower:
            label = l
            break

    return label, confidence, raw


# ── 端点 ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    load_model()


@app.get("/health")
async def health():
    return {"status": "ok", "model": str(MODEL_PATH)}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    import asyncio

    # 取最后一条 user message 的 content 作为 query
    query = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            query = msg.content
            break

    if not query:
        query = req.messages[-1].content if req.messages else ""

    t0 = time.perf_counter()
    label, confidence, raw = await asyncio.to_thread(predict_sync, query)
    latency_ms = (time.perf_counter() - t0) * 1000

    print(f"[{latency_ms:.0f}ms] {query!r} -> {label} ({confidence:.3f})")

    return ChatCompletionResponse(
        id=f"intent-{int(time.time())}",
        choices=[Choice(message=ChoiceMessage(content=label))],
        usage=Usage(),
    )


# ── 主入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    uvicorn.run(app, host="127.0.0.1", port=args.port)
