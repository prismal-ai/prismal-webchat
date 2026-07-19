# CLAUDE.md — prismal-webchat

Guidance for Claude Code (claude.ai/code) working in this repository.

## What this repo is

`prismal-webchat` is the **embeddable web chat** for the prismal ecosystem: a
[Reflex](https://reflex.dev) application (full-stack Python — React frontend +
FastAPI backend compiled from Python) that renders a streaming chat UI and can
be dropped into any web page via an `embed.js` loader + iframe. It is a
**backend-for-frontend (BFF)**: the browser talks only to this app; this app
talks to a running [`prismal-server`](https://github.com/prismal-ai/prismal-server)
exclusively through [`prismal-sdk`](https://github.com/prismal-ai/prismal-sdk)
(`AsyncPrismalClient`). The service bearer token lives server-side only.

The full design lives in
[`specs/webchat-bootstrap/`](./specs/webchat-bootstrap/) (`PLAN.md` ·
`ARCHITECTURE.md` · `SPEC.md` · `TASKS.md`). Read those before implementing.

## The one hard rule — a face, not a brain

> **intelligence → engine (`prismal`); transport → `prismal-sdk`; serving →
> `prismal-server`; rendering a conversation, per-tab session state, and
> embedding → this repo. Nothing else lives here.**

This repo imports **nothing** from `prismal` (engine) or `prismal_server`
(host), and never opens its own HTTP connection to the host (no direct
`httpx`). All upstream traffic goes through `prismal_sdk`'s typed client.
Adding agent/RAG/tool logic, prompt construction, SSE parsing, wire error-code
mapping, or webchat-side conversation persistence is a bug.

| Concern | Owner |
|---|---|
| Agent reasoning, RAG, tools, security layers | `prismal` (engine, server-side) |
| Wire contract (REST/SSE, errors, auth) | `prismal-server` (`SPEC-RHB-*`) |
| Typed transport, SSE parsing, exceptions | `prismal-sdk` (`SPEC-CSB-*`) |
| Chat UI, streaming render, embedding, branding | **this repo** (`SPEC-WCB-*`) |

## Review checklist (enforce on every PR)

- [ ] No import of `prismal` or `prismal_server`, and no direct `httpx` use,
      anywhere in `prismal_webchat/` — the AST boundary-guard test must stay
      green (`SPEC-WCB-APP-002`).
- [ ] Visitor input reaches `send_message(content=…)` **unmodified** — no
      templating, prefixing, or prompt building anywhere (`SPEC-WCB-CHT-006`).
- [ ] The bearer token (`WebchatSettings.token`, `SecretStr`) never appears in
      any `rx.State` field, event payload, compiled frontend asset, log line,
      or error message (`SPEC-WCB-AUT-002`); settings objects never cross into
      state — only derived non-secret presentation values do.
- [ ] SDK exceptions are caught only in the streaming handler and rendered as
      friendly text; no codes, server messages, or tracebacks reach the
      visitor (`SPEC-WCB-ERR-001/002`).
- [ ] No auto-retry of chat turns — retry is a visitor action, same content,
      same `thread_id` (`SPEC-WCB-ERR-004`).
- [ ] Cancellation = breaking out of the event iterator (SDK closes the
      stream, host cancels the run) — never an invented cancel RPC
      (`SPEC-WCB-CHT-005`).
- [ ] Embedding stays CSP-enforced: `frame-ancestors` from `embed_origins`,
      empty ⇒ `'self'`; `embed.js` contains no secret, org id, or host URL
      (`SPEC-WCB-EMB-002/004`).
- [ ] New behaviour is **test-first (TDD)**: failing test → minimal code →
      green. Unit tests use `FakeAsyncPrismalClient` (offline, no frontend
      compile); anything touching a live server goes in the opt-in
      `tests/contract/` suite (`SPEC-WCB-NFR-001`).
- [ ] Dep pins stay `reflex>=0.8,<0.9` and `prismal-sdk>=0.1,<1`; bumps are
      deliberate PRs (`SPEC-WCB-NFR-005`).
- [ ] `ruff check .` and `mypy prismal_webchat` are clean.
- [ ] New capability traces to a `SPEC-WCB-*` requirement — if the wire
      contract must change, that is negotiated in `prismal-server` /
      `prismal-sdk` first, never invented here.

## Common commands

```bash
uv pip install -e ".[dev]"
reflex run                          # dev server (frontend + backend + WS)
uv run pytest                       # unit (offline, FakeAsyncPrismalClient)
uv run pytest -m contract           # opt-in: against a running prismal-server
uv run ruff check . && uv run ruff format --check .
uv run mypy prismal_webchat
```

Local end-to-end: start a `prismal-server` (`uvicorn prismal_server.app:app`)
and point the webchat at it via `PRISMAL_WEBCHAT_SERVER_URL` (defaults to
`http://localhost:8000`).

## Boundary examples

- Need the answer streamed token-by-token? **Already have it** — iterate
  `client.send_message(...)` and `yield` per `TokenEvent`; never parse SSE
  yourself.
- Need conversation history after a reload? **No webchat DB** — history lives
  in the engine's checkpointer under the tab's `thread_id`; multi-conversation
  UI is `WCB-FUTURE-02`, not a quick add.
- Want to improve answers with a system prompt or RAG tweak? **No** — that is
  engine configuration, server-side. This repo passes content through.
- Need per-visitor identity or limits? **Not in v0.1** — one service
  credential; per-visitor identity is `WCB-FUTURE-03` and the engine's
  tenancy/budget layers already exist server-side.
- Want the widget on a new customer site? Add the origin to
  `PRISMAL_WEBCHAT_EMBED_ORIGINS` — never loosen the CSP logic itself.
