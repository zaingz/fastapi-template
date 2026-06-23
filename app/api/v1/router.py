from fastapi import APIRouter

from app.api.v1.endpoints import chat, health, items

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router, prefix="/health", tags=["Health"])
v1_router.include_router(items.router, prefix="/items", tags=["Items"])
v1_router.include_router(chat.router, prefix="/chat", tags=["AI"])
