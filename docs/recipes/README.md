# Recipes

Opt-in integrations. **None are core dependencies** — the default path stays key-free and offline.
Each recipe conforms to an existing Protocol (`ChatProvider`, `CacheBackend`, `RateLimiter`,
`VectorStore`) with a **lazy import**, so the SDK loads only when you select that backend.

Install a recipe's deps as an optional extra, e.g. `uv add --optional <group> <pkg>`, then
`uv sync --extra <group>`. The bundled `redis` extra is already declared in `pyproject.toml`.

## LLM providers (`ChatProvider`)
- [OpenAI](openai.md)
- [Anthropic](anthropic.md)
- [Pydantic AI](pydantic-ai.md)
- [LangGraph / LangChain](langgraph.md)

## Caching & rate limiting
- [Redis cache backend (`CacheBackend`)](redis-cache.md)
- [Redis rate limiter (`RateLimiter`)](redis-rate-limit.md)

## Retrieval
- [Vector store (pgvector / Qdrant) — `VectorStore` sketch](vector-store.md)

## Ops
- [Metrics & tracing (Prometheus / OpenTelemetry)](metrics-tracing.md)

## The rule every recipe follows

1. Implement the Protocol exactly (`name`, async methods).
2. **Lazy-import** the SDK inside the class/function — never at module top level on the default path.
3. Add the SDK as an optional extra; add any settings to `Settings` **and** `.env.example`
   (`SecretStr` for keys).
4. Wire it into the relevant `build_*()` selector keyed on a setting. Route/endpoint code stays
   provider-agnostic — it depends on the Protocol, not the concrete class.
