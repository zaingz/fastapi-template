# CLAUDE.md

@AGENTS.md is the canonical contract for this repo — setup, command contract, repo map, AI
architecture, layer rules, the vertical-slice recipe, streaming/caching/testing rules, the
Ponytail working philosophy, and the Always/Ask-first/Never boundaries. Read it; it is the source
of truth. This file adds only Claude Code–specific operating notes.

## Operating notes for Claude Code

- **Plan briefly, then act.** Get oriented fast; don't over-explore. For multi-step work, use
  TodoWrite to track progress.
- **Climb the Ponytail ladder before writing code** (see AGENTS.md): does it need to exist → reuse
  → stdlib → platform feature → installed dep → one line → minimum viable. Prefer deleting over
  adding. Leave a `ponytail:` comment at any intentional simplification, naming the upgrade path.
- **Edit minimally.** Match existing patterns (app factory, `Annotated` DI, structlog key/values,
  uniform `AppException` errors). Don't refactor or add abstractions beyond the task.
- **Never cut safety to be lazy.** Trust-boundary validation, security/secret handling, data-loss
  prevention, accessibility, typed errors, and explicitly-requested behavior are off-limits.
- **Keep the default path key-free and offline.** The `echo` provider and in-process cache must
  work with no API key and no network; real providers/Redis are opt-in, lazy-imported seams.
- **Validate before declaring done.** Run `make check` (lint + `mypy --strict` + tests) and confirm
  green. Don't silence the gate with `# type: ignore`, `# noqa`, or `--no-verify`.
- **Deletion-first review.** Before finishing, note what you removed or chose not to add, and why.
- New settings → typed `Settings` field **and** `.env.example`; secrets use `SecretStr`.
- **Caveman status prose.** Terse, exact: *what changed → why → how verified → next step.* Drop
  filler/hedging; preserve code, commands, paths, URLs, versions verbatim. Commits/PRs stay
  professional. (Full rule in AGENTS.md.)
- **Routing:** `redirect_slashes=False` — call trailing-slash endpoints (`/api/v1/chat/`).
- **Streaming changes** must test provider failure → terminal `event: error`
  (`tests/ai/test_chat_reliability.py`).
