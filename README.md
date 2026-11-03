# prismal-webchat

Embeddable web chat for the [prismal](https://github.com/prismal-ai/prismal)
ecosystem — a streaming chat widget any site can drop into a page with one
`<script>` tag, backed by a running
[`prismal-server`](https://github.com/prismal-ai/prismal-server).

Built with [Reflex](https://reflex.dev) (full-stack Python): the browser talks
to the webchat's own backend over Reflex's WebSocket, and that backend talks to
`prismal-server` exclusively through
[`prismal-sdk`](https://github.com/prismal-ai/prismal-sdk)
(`AsyncPrismalClient`; on PyPI as `prismal-ai-sdk`). This backend-for-frontend design keeps the service
bearer token server-side, needs no CORS opening on the host, and puts zero
wire-contract code in this repo.

> **Status: v0.1.0.** Chat core, silverpoint UI, AG-UI mode, embedding,
> container image and CI are implemented and tested against `prismal-server`
> 0.3 ([`CHANGELOG.md`](./CHANGELOG.md)). Design: [`specs/webchat-bootstrap/`](./specs/webchat-bootstrap/);
> progress: [`IMPLEMENTATION-PLAN.md`](./specs/webchat-bootstrap/IMPLEMENTATION-PLAN.md).

## Ecosystem position

```
browser ── Reflex WS ──▶ prismal-webchat (this repo, BFF)
                              │  prismal_sdk (HTTP + SSE)
                              ▼
                         prismal-server ──▶ prismal (engine)
```

| Repo | Role | Status |
|---|---|---|
| [`prismal`](https://github.com/prismal-ai/prismal) | Engine (LangGraph supervisor, RAG, security) — PyPI `prismal-ai` | v3.22.1 |
| [`prismal-server`](https://github.com/prismal-ai/prismal-server) | FastAPI host (REST + SSE + WS + AG-UI + A2A) | v0.3.0 |
| [`prismal-sdk`](https://github.com/prismal-ai/prismal-sdk) | Typed Python client (sync + async) — PyPI `prismal-ai-sdk` | v0.3.0 |
| [`prismal-tui`](https://github.com/prismal-ai/prismal-tui) | Terminal client (Textual) | v0.2.0 |
| `prismal-webchat` | Embeddable chat UI (this repo) | **v0.1.0** |

## What v0.1 delivers

Streaming chat (tokens render as the engine produces them), visible tool
activity, stop/cancel mid-turn, friendly retryable errors, one conversation
thread per browser tab (history lives in the engine's checkpointer), theming
via env vars, and iframe embedding with a CSP origin allowlist. See
`specs/webchat-bootstrap/PLAN.md` §5 for the full in/out-of-scope list.

## Quickstart (dev)

Requires Python 3.13 (dev target), [`uv`](https://docs.astral.sh/uv/), and a
running `prismal-server` (defaults to `http://localhost:8000`).

```bash
uv sync            # resolves prismal-ai-sdk from PyPI
uv run reflex run
# open http://localhost:3000  (webchat backend listens on :8001)
```

Point it at a server and brand it via environment variables:

```bash
export PRISMAL_WEBCHAT_SERVER_URL="https://my-prismal-server.example.com"
export PRISMAL_WEBCHAT_TOKEN="…"            # service credential, never reaches the browser
export PRISMAL_WEBCHAT_TITLE="Acme Assistant"
export PRISMAL_WEBCHAT_ACCENT_COLOR="#096D9A"   # must pass silverpoint contrast (4.5:1)
```

## Embedding

Add one tag to any page:

```html
<script src="https://chat.example.com/embed.js" async></script>
```

A floating launcher bubble injects the chat as an iframe of the bare `/chat`
route. Embedding is **disabled by default** — allow host sites explicitly:

```bash
export PRISMAL_WEBCHAT_EMBED_ORIGINS='["https://www.example.com"]'
```

The allowlist is enforced with a `frame-ancestors` CSP header (browser-level,
not spoofable in-page). Details: [`docs/embedding.md`](./docs/embedding.md).

## Install from PyPI

```bash
pip install prismal-webchat            # or: uv tool install prismal-webchat
export PRISMAL_WEBCHAT_SERVER_URL=… PRISMAL_WEBCHAT_TOKEN=…
prismal-webchat run --app-dir ./webchat   # prod, one port: http://localhost:8001
```

`prismal-webchat init DIR` only writes the Reflex working directory
(`rxconfig.py`, `assets/`, `reflex.lock/`); `prismal-webchat run --env dev`
starts the dev server instead. The first run downloads bun and the frontend
packages into the app directory.

## Deploy

```bash
docker build -t prismal-webchat .
docker run -p 8001:8001 -e PRISMAL_WEBCHAT_SERVER_URL=… -e PRISMAL_WEBCHAT_TOKEN=… prismal-webchat
```

One process, one port (`reflex run --env prod --single-port`); put a
WebSocket-capable reverse proxy with TLS in front. Released images:
`ghcr.io/prismal-ai/prismal-webchat:<version>`. Details:
[`docs/deploy.md`](./docs/deploy.md).

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PRISMAL_WEBCHAT_SERVER_URL` | `http://localhost:8000` | Target `prismal-server` |
| `PRISMAL_WEBCHAT_TOKEN` | — | Service bearer credential (server-side only) |
| `PRISMAL_WEBCHAT_ORG_ID` | — | Tenant for all webchat traffic (`X-Org-Id`) |
| `PRISMAL_WEBCHAT_TITLE` | `prismal` | Widget/page title |
| `PRISMAL_WEBCHAT_WELCOME_MESSAGE` | `Hi! How can I help?` | First assistant bubble |
| `PRISMAL_WEBCHAT_ACCENT_COLOR` | `#5D4BE5` | Accent ink; `#RRGGBB`, must pass contrast |
| `PRISMAL_WEBCHAT_THEME` | `light` | `light` \| `dark` \| `auto` |
| `PRISMAL_WEBCHAT_EMBED_ORIGINS` | `[]` | Allowed embedding origins (empty ⇒ same-origin only) |
| `PRISMAL_WEBCHAT_AGUI_ENABLED` | `false` | AG-UI event stream ([`docs/agui.md`](./docs/agui.md)) |
| `PRISMAL_WEBCHAT_SHOW_USAGE` | `false` | Show "N tokens" under replies (never cost/model) |

Full reference: [`docs/configuration.md`](./docs/configuration.md).

## Development

```bash
uv run pytest                       # unit suite — offline, fake SDK client
uv run pytest -m contract           # opt-in — against a running prismal-server (fake-LLM mode)
uv run pytest -m compile            # opt-in — compiles the frontend, scans it for secrets
uv run ruff check . && uv run mypy prismal_webchat
```

Boundary rules (no `prismal`/`prismal_server` imports, no direct HTTP to the
host, token never in the frontend) are enforced by tests — see
[`CLAUDE.md`](./CLAUDE.md) for the review checklist.

## License

[MIT](./LICENSE)
