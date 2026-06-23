# OpenAI provider

Implements `ChatProvider` with a lazy-imported `openai` SDK. The route code is unchanged — it
depends on the `ChatProvider` Protocol, not this class.

```bash
uv add --optional openai openai      # declares the optional extra
uv sync --extra openai
```

Settings (`app/core/config.py` + `.env.example`):

```python
OPENAI_API_KEY: SecretStr | None = None
```

`app/ai/providers.py`:

```python
class OpenAIChatProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        from openai import AsyncOpenAI  # lazy: keeps the default path SDK-free

        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(self, messages, *, model, temperature) -> str:
        resp = await self._client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return resp.choices[0].message.content or ""

    async def stream(self, messages, *, model, temperature):
        stream = await self._client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
```

Wire into `build_provider()`:

```python
if settings.AI_PROVIDER == "openai":
    if settings.OPENAI_API_KEY is None:
        raise ProviderConfigError(message="OPENAI_API_KEY is required for AI_PROVIDER=openai")
    return OpenAIChatProvider(settings.OPENAI_API_KEY.get_secret_value())
```

The service already enforces `AI_REQUEST_TIMEOUT` around `complete()`/`stream()` and converts a
provider failure to a terminal `error` stream event — keep that contract; do not catch and swallow
inside the provider.
