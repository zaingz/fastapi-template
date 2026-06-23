# LangGraph / LangChain adapter

LangGraph builds stateful, multi-step agent graphs; LangChain provides the model/tool abstractions.
Both fit the same seam: compile the graph once, then expose it behind the `ChatProvider` Protocol so
endpoints never import LangChain.

```bash
uv add --optional langgraph langgraph langchain-openai
uv sync --extra langgraph
```

`app/ai/providers.py`:

```python
class LangGraphChatProvider:
    name = "langgraph"

    def __init__(self) -> None:
        from langchain_openai import ChatOpenAI       # lazy imports
        from langgraph.prebuilt import create_react_agent

        # Compile once; reuse across requests. Add tools/nodes as your graph grows.
        self._graph = create_react_agent(ChatOpenAI(model="gpt-4o"), tools=[])

    @staticmethod
    def _to_lc(messages):
        return {"messages": [(m.role, m.content) for m in messages]}

    async def complete(self, messages, *, model, temperature) -> str:
        result = await self._graph.ainvoke(self._to_lc(messages))
        return result["messages"][-1].content

    async def stream(self, messages, *, model, temperature):
        # stream_mode="messages" yields (token, metadata) tuples as the graph runs.
        async for token, _meta in self._graph.astream(
            self._to_lc(messages), stream_mode="messages"
        ):
            if getattr(token, "content", ""):
                yield token.content
```

Notes:
- **Checkpointers / persistence** — LangGraph's `MemorySaver` is per-process; for durable
  multi-turn state across replicas use a Postgres/Redis checkpointer (its own opt-in dep), mirroring
  the cache/rate-limit Redis seams.
- Keep the graph compiled at construction (the `get_provider()` singleton), not per request.
- Preserve the streaming contract: surface failures to `ChatService`, which emits a terminal
  `error` event — never let an exception escape mid-stream.
