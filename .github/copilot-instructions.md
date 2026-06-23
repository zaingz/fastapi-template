See [`AGENTS.md`](../AGENTS.md) for the full contract: setup, commands, repo map, layer rules,
the endpoint vertical-slice recipe, testing rules, and Always/Ask-first/Never boundaries.

Key rules: keep HTTP out of `app/services/` (raise `AppException`, never `HTTPException`); add
config only as typed `Settings` fields documented in `.env.example`; run `make check` green before
finishing.
