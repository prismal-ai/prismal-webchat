# prismal-webchat — Embeddable WebChat (WebChat Bootstrap)

## Strategic Plan / Product Requirements Document (PLAN)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-07-19 |
| **Phase** | WCB (WebChat Bootstrap) |
| **Repository** | `prismal-ai/prismal-webchat` (this repo) |
| **Upstream contract** | `prismal-sdk >= 0.1, < 1` (typed client over the wire contract fixed by `prismal-server/specs/reference-host-bootstrap/SPEC.md`) |
| **Reviewers** | Tech Lead, AI Architect |
| **Priority** | P1 (first end-user-facing front-end of the ecosystem) |
| **Related** | `prismal-ai/prismal` (engine, v3.10.1, 21/21 specs); `prismal-ai/prismal-server` (host, v0.1 complete); `prismal-ai/prismal-sdk` (client, bootstrap complete); siblings `prismal-tui`, `prismal-dashboard`, `prismal-chatbot` (all `PENDING`) |

---

## 1. Executive Summary

`prismal` (the engine) is a pure LangGraph library. `prismal-server` put it on
the network with a fixed wire contract (REST + SSE chat, standard A2A v0.3.x).
`prismal-sdk` wrapped that contract in a typed Python client (`PrismalClient` /
`AsyncPrismalClient`) precisely so that front-end repos would never hand-roll
SSE parsing or error mapping again.

`prismal-webchat` is the first of those front-ends: an **embeddable web chat
widget** that any site can drop into a page to talk to a running
`prismal-server`. It is built with **Reflex** (full-stack Python, compiles to
React + FastAPI), which makes it a Python application end to end — the browser
talks to the webchat's own Reflex backend over Reflex's WebSocket, and that
backend talks to `prismal-server` through `AsyncPrismalClient`. This is a
**backend-for-frontend (BFF)** design: the bearer token for `prismal-server`
lives only server-side, the browser never sees the wire contract, and
`prismal-server` needs no CORS opening for end users.

This PLAN scopes **v0.1**: a streaming chat UI (tokens render as the engine
produces them), one conversation thread per visitor tab, an `embed.js` loader
that injects the chat as a floating iframe into any host page, and
theming/config via environment variables. `ARCHITECTURE.md`, `SPEC.md`, and
`TASKS.md` in this folder refine it into a buildable, test-first plan.

---

## 2. Context and Problem

- Per the `prismal-ai` ecosystem presentation (2026-07-07, v3.10.1): 8
  repositories. `prismal` and `prisma-notebooks` are `LISTO`; `prismal-server`
  v0.1 is complete (streaming chat SSE, inbound A2A, auth/tenancy, release
  plumbing); `prismal-sdk` bootstrap is complete (typed sync/async clients, 33
  offline tests green). `prismal-webchat`, `prismal-tui`, `prismal-dashboard`,
  and `prismal-chatbot` are `PENDIENTE`.
- The ecosystem layer diagram places the four front-ends **on top of
  `prismal-sdk`** — they consume the typed client, not the raw wire contract.
  `prismal-sdk`'s own SDD reinforces this: a JS/TS SDK for a pure-browser
  widget was explicitly deferred (`CSB-FUTURE-03`, "separate repo, not this
  one"). Choosing Reflex resolves that tension without waiting for a JS SDK:
  the webchat's chat logic runs in Python, where `prismal-sdk` already exists.
- Without a webchat, the only ways to talk to a running `prismal-server` are
  `curl`, the SDK from a script, or a generic A2A peer — nothing an end user
  or a product demo can use. The webchat is the ecosystem's first
  human-facing surface and its de facto live demo.
- A browser widget that talked to `prismal-server` directly would force the
  bearer token into the page (or force anonymous mode), require CORS
  (`cors_origins` exists in `HostSettings` but defaults to `[]`), and
  duplicate SSE parsing in TypeScript. The BFF design avoids all three.

---

## 3. Target Users

- **Site owners / integrators** who want to embed a prismal-backed assistant
  into an existing web page with one `<script>` tag and zero build-step
  changes.
- **End users (visitors)** chatting with the agent — they need streaming
  responses, visible tool activity, and graceful errors; they never
  authenticate against `prismal-server` themselves.
- **The prismal-ai org itself** — the webchat doubles as the standard live
  demo of the engine + host + SDK stack.
- **`prismal-dashboard` maintainers** — the chat panel patterns (streaming
  state, event rendering) established here are reusable in the dashboard.

---

## 4. Goals and Success Metrics

| Goal | Metric | Target |
|---|---|---|
| Streaming chat UI | Tokens render incrementally as `prismal-server` emits them | A full turn streams end-to-end against a local host with no visible buffering of the whole answer |
| Embeddable | A plain HTML page adds the widget with one `<script src=".../embed.js">` tag | Floating bubble opens/closes the chat iframe on an arbitrary host page |
| Zero wire-contract code | No SSE parsing, error-code mapping, or JSON-RPC framing in this repo | All transport goes through `prismal_sdk`; enforced by an AST import/usage-guard test |
| Secret hygiene | The `prismal-server` bearer token never reaches the browser | Token lives in backend-only settings (`SecretStr`); an automated test asserts it is absent from compiled frontend state and page payloads |
| Offline-testable | Unit suite runs with no live server | A fake `AsyncPrismalClient` double; opt-in `contract` suite hits a real host |
| Installable via uv | `uv pip install -e ".[dev]"` + `reflex run` from a fresh clone | App boots, lints, type-checks, tests green |

---

## 5. Scope

### In scope (v0.1 — the minimal viable webchat)

- Reflex application `prismal_webchat`: chat page (message list, input bar,
  send button) with per-tab conversation state.
- Streaming turn lifecycle: send → `TokenEvent` deltas appended live →
  `ToolCallEvent` shown as an activity indicator ("using web_search…") →
  `DoneEvent` closes the turn; typed SDK exceptions render as an in-chat
  error bubble with retry.
- Thread management: lazily `create_thread()` on the first message of a tab;
  reuse the `thread_id` for the rest of the session (engine-side checkpointer
  keeps history under that thread).
- Cancellation: a "stop" affordance while streaming; leaving/closing the tab
  stops consumption so the SDK closes the HTTP stream and the host cancels
  the run (`SPEC-RHB-CHT-004` chain).
- Embedding: `embed.js` loader script (floating launcher bubble + iframe) and
  a bare `/chat` route suitable for direct iframing; minimal `postMessage`
  API (`open`/`close`); configurable allowed embedding origins.
- Configuration via `PRISMAL_WEBCHAT_` environment variables: target server,
  token, org, branding (title, welcome message, accent color), embedding
  origins.
- Theming: light/dark + accent color, applied to both the full page and the
  embedded widget.
- Unit test suite offline (fake SDK client); opt-in `contract` suite against
  a running `prismal-server`.
- `uv`-based dev foundation: `pyproject.toml`, `ruff`, `mypy`, `pytest` +
  `pytest-asyncio`, CI workflow; Dockerfile for one-container deploy.

### Out of scope (deferred)

- **Multi-conversation history / persistence UI** — v0.1 is one thread per
  tab; listing or resuming past threads is a dashboard concern
  (`prismal-dashboard`) or a later phase (WCB-FUTURE-02).
- **End-user authentication** (visitor login, per-user identity) — v0.1
  visitors are anonymous to the webchat; the webchat authenticates itself to
  `prismal-server` with one service credential. Per-visitor identity mapping
  is WCB-FUTURE-03.
- **A2A surface** — the webchat is a chat consumer; it does not expose or
  consume A2A. Generic A2A peers already talk to `prismal-server` directly.
- **File/media upload** — the engine's multimodal layer is opt-in and the
  chat contract carries text `content` only in v0.1; revisit when the host
  specs a media upload route (WCB-FUTURE-04).
- **Pure-JS standalone widget (no Python backend)** — would require the
  deferred JS/TS SDK (`CSB-FUTURE-03` in `prismal-sdk`) plus CORS + token
  exposure decisions on the host; explicitly not this repo's v0.1
  (WCB-FUTURE-05).
- **Horizontal scale-out concerns** (sticky sessions, external state store
  for Reflex) — single-process deploy in v0.1; documented as a deploy note,
  solved when real load exists (WCB-FUTURE-06).

---

## 6. Functional Requirements (summary; refined in `SPEC.md`)

| ID | Requirement | Priority |
|---|---|---|
| RF-WCB-001 | Reflex chat UI with per-tab state: message list, input, send; welcome message | `MUST` |
| RF-WCB-002 | Streaming turn lifecycle over `AsyncPrismalClient.send_message()`: live token deltas, tool activity, done/error terminal states | `MUST` |
| RF-WCB-003 | Thread lifecycle: lazy `create_thread()`, thread reuse per tab, stop/cancel affordance | `MUST` |
| RF-WCB-004 | Embedding: `embed.js` loader + iframeable `/chat` route + origin allowlist | `MUST` |
| RF-WCB-005 | All `prismal-server` communication goes through `prismal_sdk`; zero wire-contract code and zero `prismal`/`prismal_server` imports here | `MUST` |
| RF-WCB-006 | Server-side configuration (`PRISMAL_WEBCHAT_` prefix); token as `SecretStr`, never serialized to the frontend | `MUST` |
| RF-WCB-007 | Error UX: typed SDK exceptions mapped to friendly in-chat messages with retry; no stack traces or codes leaked to visitors | `MUST` |
| RF-WCB-008 | Theming/branding via config (title, welcome, accent, light/dark) | `SHOULD` |
| RF-WCB-009 | Offline unit suite (fake SDK client) + opt-in `contract` suite against a live host | `MUST` |

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep — webchat grows agent/business logic (prompting, RAG, retries) | `CLAUDE.md` hard rule + review checklist: UI, session mapping, and presentation only; the engine owns intelligence, the SDK owns transport |
| Wire-contract drift reaches the UI | The SDK absorbs contract changes; this repo pins `prismal-sdk>=0.1,<1` and upgrades deliberately; `contract` suite catches breakage |
| Token leaks into the compiled frontend | Backend-only settings object (never `rx.State` fields); `SecretStr`; a dedicated test greps compiled output and state payloads for the secret |
| Reflex WebSocket vs. long streams (proxy timeouts, tab close) | Streaming handlers yield per event (built-in keepalive via state updates); disconnect stops iteration → SDK closes the SSE stream → host cancels the run |
| Embedding abuse (arbitrary sites iframing the chat) | `frame-ancestors` CSP built from `PRISMAL_WEBCHAT_EMBED_ORIGINS`; empty list = same-origin only |
| Reflex major-version churn | Pin a tested minor (`reflex>=0.8,<0.9` at seed time); upgrades are deliberate tasks, not drive-by |
| Single service credential = one shared budget/tenant for all visitors | Acceptable for v0.1 (documented); per-visitor identity is WCB-FUTURE-03 and the engine's budget/tenancy layers already exist server-side |

---

## 8. Dependencies

- `prismal-sdk` — the **only** path to `prismal-server`. Typed models,
  streaming events, exception hierarchy. No other prismal dependency.
- `reflex` — full-stack Python web framework (React + FastAPI compiled);
  chosen by explicit stack decision (ADR-001 in `ARCHITECTURE.md`).
- Dev-only: `pytest`, `pytest-asyncio`, `ruff`, `mypy`.
- A running `prismal-server` for `contract` tests and manual dev (local
  `uvicorn` or Docker; see that repo's docs).
- **Not** dependencies: `prismal` (engine), `prismal_server` (host), `httpx`
  as a direct dep (it arrives transitively via the SDK and must not be used
  directly here — enforced by the boundary test).

---

## 9. Milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| M0 — Seed | This SDD set (`PLAN`/`ARCHITECTURE`/`SPEC`/`TASKS`) + repo `CLAUDE.md` + `README.md` | Reviewed & merged |
| M1 — App skeleton | `uv` scaffold, Reflex app boots, settings (`PRISMAL_WEBCHAT_`), boundary guard test, CI | `reflex run` serves an empty chat page; guards green |
| M2 — Chat core | Send/receive one full streaming turn against a fake SDK client; thread lifecycle | Unit-tested turn: tokens append live, done closes, error renders |
| M3 — Chat UX | Tool-activity indicator, stop/cancel, retry-on-error, welcome message, theming | All `SPEC-WCB-CHT-*` / `ERR-*` green offline |
| M4 — Embedding | `/chat` iframe route, `embed.js` launcher, `postMessage` open/close, origin allowlist CSP | Widget opens on a plain HTML demo page from an allowed origin; blocked otherwise |
| M5 — Hardening & release | `contract` suite vs a real host, secret-leak test, Dockerfile, docs, `v0.1.0` tag | CI green; one-container deploy chats against a live `prismal-server` |

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-19 | Ernesto Crespo | Initial PLAN for the embeddable webchat, derived from the ecosystem presentation (v3.10.1), the `prismal-server` wire contract, and the `prismal-sdk` client surface; stack decision: Reflex |
