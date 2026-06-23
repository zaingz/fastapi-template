# Pydantic AI provider

[Pydantic AI](https://ai.pydantic.dev/) gives typed agents with structured outputs and tool calling
over many model backends, while staying ergonomic with FastAPI. Wrap an `Agent` behind the
`ChatProvider` Protocol so routes stay provider-agnostic.

```bash
uv add --optional pydantic-ai pydantic-ai-slim
uv sync --extra pydantic-ai
```

`app/ai/providers.py`:

```python
class PydanticAIChatProvider:
    name = "pydantic-ai"

    def __init__(self, model: str) -> None:
        from pydantic_ai import Agent  # lazy import

        self._agent = Agent(model)  # model id selects the backend, e.g. "openai:gpt-4o"

    async def complete(self, messages, *, model, temperature) -> str:
        from pydantic_ai.messages import ModelRequest

        history = [ModelRequest.user_text_prompt(m.content) for m in messages if m.role == "user"]
        result = await self._agent.run(message_history=history)
        return str(result.output)

    async def stream(self, messages, *, model, temperature):
        prompt = next((m.content for m in reversed(messages) if m.role == "user"), "")
        async with self._agent.run_stream(prompt) as stream:
            async for chunk in stream.stream_text(delta=True):
                yield chunk
```

Use Pydantic AI when you want **structured/validated outputs** or **typed tool calls** rather than
raw text. For multi-step orchestration with shared state, prefer LangGraph
([recipe](langgraph.md)). Keep the `AI_REQUEST_TIMEOUT` + terminal-`error` streaming contract
intact — let exceptions surface to the service, which converts them.
