# Anthropic (Claude) provider

Implements `ChatProvider` with a lazy-imported `anthropic` SDK. Default to the latest Claude models
(e.g. `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`). Anthropic takes the system prompt
as a separate field, not a message role — split it out.

```bash
uv add --optional anthropic anthropic
uv sync --extra anthropic
```

Settings:

```python
ANTHROPIC_API_KEY: SecretStr | None = None
```

`app/ai/providers.py`:

```python
class AnthropicChatProvider:
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        from anthropic import AsyncAnthropic  # lazy import

        self._client = AsyncAnthropic(api_key=api_key)

    @staticmethod
    def _split(messages):
        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        return system or None, turns

    async def complete(self, messages, *, model, temperature) -> str:
        system, turns = self._split(messages)
        resp = await self._client.messages.create(
            model=model, max_tokens=1024, temperature=temperature, system=system, messages=turns
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    async def stream(self, messages, *, model, temperature):
        system, turns = self._split(messages)
        async with self._client.messages.stream(
            model=model, max_tokens=1024, temperature=temperature, system=system, messages=turns
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

Wire into `build_provider()` keyed on `AI_PROVIDER == "anthropic"`, raising `ProviderConfigError`
when the key is missing. Prompt caching: enable Anthropic prompt caching for repeated system
prompts/tools to cut cost and latency.
