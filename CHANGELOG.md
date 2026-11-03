# Changelog

All notable changes to `prismal-webchat`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Releases ship as a container image
(`ghcr.io/prismal-ai/prismal-webchat`), not to PyPI.

## [Unreleased]

## [0.1.0] — 2026-11-03

First release: the embeddable web chat for the prismal ecosystem, a Reflex
backend-for-frontend that talks to `prismal-server` 0.3 only through
`prismal-ai-sdk` (`specs/webchat-bootstrap/`, DELTA-2026-10, DELTA-2026-11,
DELTA-2026-11-pypi).

### Added

- **Streaming chat.** Tokens render as the engine produces them, tool activity
  shows as chips, one turn in flight per tab, **Stop** cancels mid-turn by
  closing the SDK stream, and visitor input reaches the host unmodified. One
  conversation thread per browser tab; history lives in the engine's
  checkpointer.
- **AG-UI mode** (`PRISMAL_WEBCHAT_AGUI_ENABLED`): AG-UI 1.0 events mapped to
  the same view (text, tool chips keyed by call id, sub-agent line), with a
  one-time fallback to the native stream when the host has AG-UI disabled.
  An interrupted run ends the turn; there is no resume UI yet.
- **Usage footer** (`PRISMAL_WEBCHAT_SHOW_USAGE`): opt-in "N tokens" under a
  reply; cost and model never reach the browser.
- **Friendly errors.** SDK exceptions become plain-language bubbles
  (unreachable, request denied — including the host's `forbidden` /
  `forbidden_tenant` — and generic) with a visitor-driven **Retry** of the
  same content on the same thread, never an automatic one. A budget refusal
  shows a "usage limit" bubble with no retry.
- **UI** composed from `reflex-silverpoint-react` primitives: light, dark
  (cyanotype) and `auto` themes, accent colour validated for contrast at
  startup, markdown with raw HTML disabled, `role=log` + `aria-live`.
- **Embedding.** `<script src=".../embed.js">` adds a launcher and lazily
  frames the bare `/chat` route. Embedding is off by default; the
  `frame-ancestors` CSP comes from `PRISMAL_WEBCHAT_EMBED_ORIGINS`. The
  loader carries no URL, tenant or secret, and only obeys messages from the
  webchat origin.
- **Configuration** via `PRISMAL_WEBCHAT_*` env vars, validated at startup;
  the bearer token is a `SecretStr` that never enters state, logs, events or
  compiled assets.
- **Container image** (`Dockerfile`): one `reflex run --env prod
  --single-port` process on port 8001, non-root, frontend built at startup
  from the runtime branding with no network access. `docs/deploy.md` covers
  the reverse proxy (WebSocket upgrade) and the single-process limit.
- **CI** (`ci.yml`): ruff, mypy strict and the offline unit suite on every
  push; on pull requests also the contract suite against `prismal-server`
  0.3 from PyPI in fake-LLM mode, the compile secret-scan and a Docker smoke
  test. **Release** (`release.yml`): from `main`, pushes the GHCR image and
  creates the `v<version>` tag and GitHub release.

### Dependencies

- `reflex>=0.10,<0.11`, `reflex-silverpoint-react>=0.9.1,<0.10`,
  `prismal-ai-sdk>=0.3,<1` (the PyPI name of `prismal-sdk`),
  `pydantic-settings>=2.5,<3`. Python `>=3.11`.

[Unreleased]: https://github.com/prismal-ai/prismal-webchat/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/prismal-ai/prismal-webchat/releases/tag/v0.1.0
