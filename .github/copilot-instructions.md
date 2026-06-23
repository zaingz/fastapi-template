See [`AGENTS.md`](../AGENTS.md) for the full contract: setup, commands, repo map, layer rules,
the endpoint vertical-slice recipe, testing rules, and Always/Ask-first/Never boundaries.

Key rules: climb the Ponytail ladder before writing code (reuse → stdlib → platform → installed
dep → minimum viable) but never cut safety carve-outs; keep HTTP out of `app/services/` and
`app/ai/service.py` (raise `AppException`, never `HTTPException`); keep the default `echo` provider
key-free and offline; cache non-streaming completions only; add config only as typed `Settings`
fields documented in `.env.example`; run `make check` green before finishing.
