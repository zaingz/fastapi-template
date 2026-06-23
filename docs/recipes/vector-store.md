# Vector store (pgvector / Qdrant)

Vector search is **not** a core dependency. When you add retrieval, introduce a `VectorStore`
Protocol that mirrors the `ChatProvider`/`CacheBackend` seams — async, HTTP-agnostic, lazy-imported
SDK — so the rest of the app depends on the interface, not the engine.

## Protocol sketch (`app/ai/vector.py`)

```python
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class VectorMatch:
    id: str
    score: float
    metadata: dict[str, str]


@runtime_checkable
class VectorStore(Protocol):
    """Async vector index. Embeddings are computed by the caller (or a provider seam)."""

    async def upsert(self, id: str, embedding: list[float], metadata: dict[str, str]) -> None: ...

    async def query(self, embedding: list[float], *, top_k: int) -> list[VectorMatch]: ...
```

## pgvector (Postgres) implementation guidance

```bash
uv add --optional pgvector "sqlalchemy[asyncio]" asyncpg pgvector
```

- Add the `vector` extension and a `vector(<dim>)` column; index with HNSW or IVFFlat for ANN.
- Query with the `<=>` (cosine) / `<->` (L2) distance operators, `ORDER BY embedding <=> :q LIMIT k`.
- Reuse one async engine created in `lifespan.py` (`app.state.db_engine`); never open a connection
  per request. Best when you already run Postgres and want transactional co-location of rows +
  vectors.

## Qdrant implementation guidance

```bash
uv add --optional qdrant qdrant-client
```

- Lazy-import `AsyncQdrantClient`; create a collection with the right `size` + `Distance`.
- `upsert` points with payload; `query` via `query_points(..., limit=top_k)`.
- Best as a dedicated, horizontally-scalable vector service decoupled from your primary DB.

## Wiring

Add a `build_vector_store(settings)` selector keyed on a `VECTOR_BACKEND` setting (default: none /
disabled), and a `get_vector_store()` singleton — exactly like `get_provider()`/`get_cache()`.
Embeddings come from an embedding provider behind its own seam; keep the default build offline (no
backend configured = retrieval disabled).
