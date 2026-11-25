import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import get_settings
from app.messages.routes import router as messages_router
from app.rag_client import get_rag_client
from app.sessions.routes import router as sessions_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    rag = get_rag_client()
    await rag.start()
    try:
        yield
    finally:
        await rag.stop()


settings = get_settings()
app = FastAPI(title="Jtron Maintenance RAG", lifespan=lifespan)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(messages_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
