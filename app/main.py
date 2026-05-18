from fastapi import FastAPI

from app.routes.chat import router as chat_router

app = FastAPI(title="MobileAssist-Agent", version="0.1.0")
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
