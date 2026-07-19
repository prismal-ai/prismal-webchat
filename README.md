# prismal-webchat

Embeddable web chat for the [prismal](https://github.com/prismal-ai/prismal)
ecosystem — a streaming chat widget any site can drop into a page with one
`<script>` tag, backed by a running
[`prismal-server`](https://github.com/prismal-ai/prismal-server).

Built with [Reflex](https://reflex.dev) (full-stack Python): the browser talks
to the webchat's own backend over Reflex's WebSocket, and that backend talks to
`prismal-server` exclusively through
[`prismal-sdk`](https://github.com/prismal-ai/prismal-sdk)
(`AsyncPrismalClient`). This backend-for-frontend design keeps the service
bearer token server-side, needs no CORS opening on the host, and puts zero
wire-contract code in this repo.

> **Status: bootstrap (SDD seed).** The design is complete in
> [`specs/webchat-bootstrap/`](./specs/webchat-bootstrap/)
> (`PLAN.md` · `ARCHITECTURE.md` · `SPEC.md` · `TASKS.md`); implementation
> phases WCB-00…04 are tracked in `TASKS.md`.

## Ecosystem position

```
browser ── Reflex WS ──▶ prismal-webchat (this repo, BFF)
                              │  prismal_sdk (HTTP + SSE)
                              ▼
                         prismal-server ──▶ prismal (engine)
```

| Repo | Role | Status |
|---|---|---|
| [`prismal`](https://github.com/prismal-ai/prismal) | Engine (LangGraph supervisor, 29 routes, RAG, security) | v3.10.1 — 21/21 specs |
| [`prismal-server`](https://github.com/prismal-ai/prismal-server) | FastAPI host (REST + SSE + A2A) | v0.1 complete |
| [`prismal-sdk`](https://github.com/prismal-ai/prismal-sdk) | Typed Python client (sync + async) | bootstrap complete |
| `prismal-webchat` | Embeddable chat UI (this repo) | **SDD seed** |

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
uv pip install -e ".[dev]"
reflex run
# open http://localhost:3000
```

Point it at a server and brand it via environment variables:

```bash
export PRISMAL_WEBCHAT_SERVER_URL="https://my-prismal-server.example.com"
export PRISMAL_WEBCHAT_TOKEN="…"            # service credential, never reaches the browser
export PRISMAL_WEBCHAT_TITLE="Acme Assistant"
export PRISMAL_WEBCHAT_ACCENT_COLOR="#0EA5E9"
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
not spoofable in-page). Details: `docs/embedding.md` (Phase 4).

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PRISMAL_WEBCHAT_SERVER_URL` | `http://localhost:8000` | Target `prismal-server` |
| `PRISMAL_WEBCHAT_TOKEN` | — | Service bearer credential (server-side only) |
| `PRISMAL_WEBCHAT_ORG_ID` | — | Tenant for all webchat traffic (`X-Org-Id`) |
| `PRISMAL_WEBCHAT_TITLE` | `prismal` | Widget/page title |
| `PRISMAL_WEBCHAT_WELCOME_MESSAGE` | `Hi! How can I help?` | First assistant bubble |
| `PRISMAL_WEBCHAT_ACCENT_COLOR` | `#6C5CE7` | Accent color |
| `PRISMAL_WEBCHAT_THEME` | `light` | `light` \| `dark` \| `auto` |
| `PRISMAL_WEBCHAT_EMBED_ORIGINS` | `[]` | Allowed embedding origins (empty ⇒ same-origin only) |

## Development

```bash
uv run pytest                       # unit suite — offline, fake SDK client
uv run pytest -m contract           # opt-in — against a running prismal-server
uv run ruff check . && uv run mypy prismal_webchat
```

Boundary rules (no `prismal`/`prismal_server` imports, no direct HTTP to the
host, token never in the frontend) are enforced by tests — see
[`CLAUDE.md`](./CLAUDE.md) for the review checklist.

## License

[MIT](./LICENSE)
