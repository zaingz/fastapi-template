# 0002 — AI application building blocks

- Status: Accepted
- Date: 2026-06-23

## Context

The template should let developers start an AI application immediately, while staying minimal,
production-shaped, and friendly to coding agents. "Batteries-included" must mean *the right seams
are present and working*, not *every AI framework is bundled*. A clone must run with no API key and
no external services so the first experience is instant and tests are hermetic.

## Decision

1. **AI domain in `app/ai/`** — a dedicated package (`schemas`, `providers`, `cache`, `service`)
   sitting at the same layer as `services/`. Import direction stays inward: `api → services → ai →
   core`. The service holds business logic and no HTTP primitives, consistent with ADR-0001.
2. **Provider seam, echo by default** — a `ChatProvider` Protocol (async `complete`/`stream`) with
   a zero-dependency `EchoChatProvider` as the default. Real providers (OpenAI, Anthropic, LiteLLM)
   are a documented seam in `build_provider()`, added behind lazy imports and opt-in extras. No SDK
   or key is on the default path.
3. **Streaming via Starlette `StreamingResponse`** — SSE with typed events (`start`/`token`/`done`/
   `error`), no extra dependency (`sse-starlette` rejected as unnecessary). Streams are `no-store`.
4. **Caching as a `CacheBackend` Protocol** — default `InMemoryTTLCache` (TTL + LRU, stdlib only),
   a process-wide singleton. The cache key includes provider, model, prompt version, temperature,
   and messages. Only non-streaming completions are cached. Redis is a documented seam, not bundled.
5. **Config-driven, secret-safe** — `AI_PROVIDER`, `AI_MODEL`, `AI_PROMPT_VERSION`, cache TTL/size,
   and optional `OPENAI_API_KEY: SecretStr` are typed `Settings` fields documented in `.env.example`.
6. **Ponytail working philosophy** — encoded in `AGENTS.md`/`CLAUDE.md`: a decision ladder favoring
   reuse/stdlib/platform over new code, never-cut safety carve-outs, the `ponytail:` comment
   convention for intentional simplifications, and a deletion-first review pass.

## Consequences

- Cloning yields a working chat API (non-streaming + streaming, cached) with no setup.
- Adding a real provider is a small, well-marked change; heavy deps never burden the default install.
- The in-process cache is per-replica; shared caching is an explicit, deferred upgrade.
- Deliberately **not** built: RAG/vector DB, background queues, eval frameworks, MCP/LangGraph
  scaffolds, multi-provider routing — each is bloat for a starter and is left as a documented seam.

## Agent rules derived from this decision

- Keep the default path key-free and offline; never require a key for `echo` or for tests.
- Providers and the cache are HTTP-agnostic; combine them only in `ChatService`.
- Cache non-streaming completions only; bump `AI_PROMPT_VERSION` when prompt construction changes.
- Add provider SDKs/Redis as opt-in optional dependencies, lazy-imported — never on the default path.
- Use Starlette `StreamingResponse` for SSE; emit a terminal `error` event instead of leaking
  exceptions mid-stream.
