See [`AGENTS.md`](../AGENTS.md) for the full contract: setup, commands, repo map, layer rules,
the endpoint vertical-slice recipe, testing rules, and Always/Ask-first/Never boundaries.

Key rules: climb the Ponytail ladder before writing code (reuse → stdlib → platform → installed
dep → minimum viable) but never cut safety carve-outs; keep HTTP out of `app/services/` and
`app/ai/service.py` (raise `AppException`, never `HTTPException`); keep the default `echo` provider
key-free and offline; cache non-streaming completions only; add config only as typed `Settings`
fields documented in `.env.example`; run `make check` green before finishing.

More rules: routes use `redirect_slashes=False` — call trailing-slash endpoints (`/api/v1/chat/`);
streaming changes must test a provider failure → terminal `event: error` (never a leaked exception
mid-stream); the ASGI server owns the bind (`gunicorn.conf.py` reads `$PORT`/`$WEB_CONCURRENCY`),
not app `Settings`. Status prose is Caveman: terse and exact — *what changed → why → how verified →
next step* — but commits and PRs stay professional.
