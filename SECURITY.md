# Security Policy

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Report privately via GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
("Report a vulnerability" under the repository **Security** tab). Include reproduction steps,
affected version/commit, and impact. Expect an acknowledgement within a few business days.

## Scope

This is a template. The most valuable reports concern defaults that a clone inherits:

- The default `echo` provider or in-process cache leaking data across requests.
- Secret handling (`SecretStr`, logging) exposing values.
- Trust-boundary gaps (request size/shape limits in `app/ai/schemas.py`).
- The production `SECRET_KEY` guard (`app/core/config.py`) being bypassable.

## Hardening checklist for deployments

This template ships safe defaults but the deploying operator owns production posture:

- Set `ENVIRONMENT=production`, `DEBUG=false`, `LOG_JSON=true`.
- Override `SECRET_KEY` with a strong random value — the app refuses to boot in production on the
  shipped placeholder.
- Provide secrets (`SECRET_KEY`, provider API keys) via the platform secret store, never baked into
  the image or committed in `.env`.
- Restrict `CORS_ORIGINS` to the origins you actually serve.
- Add authentication, rate limiting, and a shared cache/store as your needs grow (documented seams
  in [`docs/architecture.md`](./docs/architecture.md)).
