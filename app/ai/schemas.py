from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]

# Trust-boundary limit: caps request size regardless of provider. Keep in sync with docs.
MAX_MESSAGE_CHARS = 8_000
MAX_MESSAGES = 50


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=MAX_MESSAGES)
    model: str | None = Field(default=None, description="Override the configured default model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    model: str
    content: str
    cached: bool = False


class ChatStreamEvent(BaseModel):
    """A single Server-Sent Event in a streaming chat response."""

    event: Literal["start", "token", "done", "error"]
    data: dict[str, Any]

    def to_sse(self) -> str:
        from json import dumps

        return f"event: {self.event}\ndata: {dumps(self.data, separators=(',', ':'))}\n\n"
