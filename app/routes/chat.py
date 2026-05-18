import time

from fastapi import APIRouter

from app.models.request import ChatRequest
from app.models.response import ChatResponse
from app.services.intent.classifier import IntentClassifier
from app.services.memory.session_store import SessionStore
from app.services.routing.router import Router

import asyncio

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    t0 = time.perf_counter()

    # 并发执行：记忆读取 + 意图分类
    history, intent_result = await asyncio.gather(
        SessionStore.get(req.session_id),
        IntentClassifier.predict(req.query),
    )

    # 根据意图分发到对应链路
    result = await Router.dispatch(
        query=req.query,
        intent=intent_result,
        history=history,
    )

    # 更新记忆
    await SessionStore.update(req.session_id, req.query, result.response)

    latency = (time.perf_counter() - t0) * 1000
    return ChatResponse(
        response=result.response,
        intent=intent_result.label,
        tools_used=result.tools_used,
        latency_ms=round(latency, 2),
    )
