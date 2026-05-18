from pydantic import BaseModel


class ChatResponse(BaseModel):
    response: str
    intent: str
    tools_used: list[str]
    latency_ms: float
