from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.cache import CacheBackend, get_cache
from app.ai.providers import ChatProvider, get_provider
from app.ai.schemas import ChatRequest, ChatResponse
from app.ai.service import ChatService
from app.core.dependencies import SettingsDep

router = APIRouter()

ProviderDep = Annotated[ChatProvider, Depends(get_provider)]
CacheDep = Annotated[CacheBackend, Depends(get_cache)]


def get_chat_service(provider: ProviderDep, cache: CacheDep, settings: SettingsDep) -> ChatService:
    return ChatService(provider=provider, cache=cache, settings=settings)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("/", response_model=ChatResponse, summary="Chat completion")
async def chat(request: ChatRequest, service: ChatServiceDep) -> ChatResponse:
    """Non-streaming completion. Identical requests are served from cache."""
    return await service.complete(request)


@router.post(
    "/stream",
    summary="Streaming chat completion (SSE)",
    response_class=StreamingResponse,
)
async def chat_stream(request: ChatRequest, service: ChatServiceDep) -> StreamingResponse:
    """Server-Sent Events: `start` → `token`* → `done` (or `error`). Never cached."""

    async def event_source() -> AsyncIterator[str]:
        async for event in service.stream(request):
            yield event.to_sse()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
