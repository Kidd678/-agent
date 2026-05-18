from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class Turn:
    role: str   # "user" | "assistant"
    content: str


class SessionStore:
    """基于内存的会话记忆，保留最近 10 轮对话。"""

    _store: dict[str, deque[Turn]] = defaultdict(lambda: deque(maxlen=10))

    @classmethod
    async def get(cls, session_id: str) -> list[dict]:
        turns = cls._store[session_id]
        return [{"role": t.role, "content": t.content} for t in turns]

    @classmethod
    async def update(cls, session_id: str, query: str, response: str) -> None:
        cls._store[session_id].append(Turn("user", query))
        cls._store[session_id].append(Turn("assistant", response))

    @classmethod
    async def clear(cls, session_id: str) -> None:
        cls._store.pop(session_id, None)
