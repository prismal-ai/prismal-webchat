# prismal-webchat — Architecture (WebChat Bootstrap)

| Field | Value |
|---|---|
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-07-19 |
| **Companion** | [`PLAN.md`](./PLAN.md) · [`SPEC.md`](./SPEC.md) · [`TASKS.md`](./TASKS.md) |

---

## 1. Guiding principle — a face, not a brain

> **intelligence → engine (`prismal`); transport → `prismal-sdk`; serving the
> engine → `prismal-server`; rendering a conversation and embedding it into a
> page → this repo. Nothing else lives here.**

`prismal-webchat` talks to exactly **one** upstream: a running
`prismal-server`, and only **through `prismal_sdk`**. It never imports
`prismal` (engine) or `prismal_server` (host), never opens a raw HTTP
connection to the host (no direct `httpx` use), never parses SSE, never maps
wire error codes, and never builds a prompt. Its whole job is:

| Concern | Owner |
|---|---|
| Agent reasoning, RAG, tools, security | `prismal` (engine), server-side |
| Wire contract (REST/SSE, errors, auth headers) | `prismal-server` (SPEC-RHB-*) |
| Typed transport, SSE parsing, exceptions | `prismal-sdk` (SPEC-CSB-*) |
| Chat UI, per-tab session state, streaming render, embedding, branding | **this repo** (SPEC-WCB-*) |

Any pull toward importing `prismal.*` / `prismal_server.*`, calling the host
with `httpx` directly, re-implementing event parsing, or adding
prompt/agent/business logic is a design smell — see the `CLAUDE.md` review
checklist.

---

## 2. C4 — Context

```
                       host web page (any site)
                  ┌──────────────────────────────┐
                  │  <script src=".../embed.js"> │
                  │   launcher bubble → iframe ──┼──────────┐
                  └──────────────────────────────┘          │
                                                            ▼
   visitor browser ──── Reflex WS (state updates) ──▶ ┌────────────────────┐
                                                      │  prismal-webchat   │  this repo
                                                      │  (Reflex app:      │  Python, BFF
                                                      │   React front +    │
                                                      │   FastAPI back)    │
                                                      └─────────┬──────────┘
                                                                │ import prismal_sdk
                                                                │ (AsyncPrismalClient,
                                                                │  HTTP + SSE)
                                                                ▼
                                                      ┌────────────────────┐
                                                      │   prismal-server   │  sibling repo
                                                      └─────────┬──────────┘
                                                                │ 4 seams
                                                                ▼
                                                      ┌────────────────────┐
                                                      │  prismal (engine)  │
                                                      └────────────────────┘
```

The browser **never** talks to `prismal-server`. All engine traffic
originates from the webchat backend (BFF), which holds the single service
credential. Consequences: no `cors_origins` opening required on the host for
end users, no token in the page, no wire contract in JavaScript.

---

## 3. C4 — Container / module layout

Reflex app package `prismal_webchat`:

```
prismal-webchat/
├── pyproject.toml                  # deps: reflex, prismal-sdk; NO prismal/prismal-server/httpx dep
├── rxconfig.py                     # Reflex app config (app_name, ports)
├── CLAUDE.md                       # boundary rule + review checklist
├── README.md
├── Dockerfile                      # one-container deploy (reflex export / prod runner)
├── prismal_webchat/
│   ├── __init__.py
│   ├── webchat.py                  # rx.App assembly, routes: / (full page), /chat (bare, iframe-safe)
│   ├── settings.py                 # WebchatSettings (pydantic-settings, PRISMAL_WEBCHAT_ prefix, SecretStr token) — backend-only
│   ├── client.py                   # get_client(): lazily built, process-wide AsyncPrismalClient from settings
│   ├── state/
│   │   ├── chat.py                 # ChatState (rx.State): messages, thread_id, streaming flag, handlers
│   │   └── models.py               # UI-side dataclasses: ChatMessage(role, text, kind), ToolActivity
│   ├── components/
│   │   ├── chat_panel.py           # message list, bubbles, tool-activity chip, error bubble + retry
│   │   ├── input_bar.py            # input, send, stop
│   │   └── theme.py                # light/dark + accent from settings
│   └── embed/
│       ├── embed.js                # static loader: launcher bubble + iframe injection + postMessage
│       └── demo.html               # plain host page for manual embedding tests
├── docs/
│   ├── embedding.md                # script-tag usage, origins, postMessage API
│   ├── configuration.md            # PRISMAL_WEBCHAT_* reference
│   └── deploy.md                   # Docker, reverse proxy (WS), single-process note
└── tests/
    ├── conftest.py                 # FakeAsyncPrismalClient (scripted event streams), settings fixtures
    ├── unit/                       # state handlers, settings, error mapping, embed config (offline)
    └── contract/                   # opt-in: real prismal-server round-trip
```

**Why state handlers and not services:** Reflex's unit of behavior is the
event handler on `rx.State`. `ChatState` owns the entire turn lifecycle;
`client.py` only builds/configures the SDK client. There is no service layer
because there is no business logic to put in one — the handler maps SDK
events to UI state, one-to-one.

---

## 4. Data flow

### 4.1 Streaming chat turn (RF-WCB-002/003)

```
visitor hits Send
  │ Reflex WS event → ChatState.send()
  ├─ append ChatMessage(role="user"); clear input; yield        (input clears instantly)
  ├─ thread_id is None?  → thread = await client.create_thread(); store thread_id
  ├─ append ChatMessage(role="assistant", text=""); streaming=True; yield
  └─ async for event in client.send_message(thread_id, content):
        TokenEvent(delta)        → last message.text += delta        ; yield   (live render)
        ToolCallEvent(name,args) → tool_activity = name              ; yield   (chip: "using web_search…")
        StateEvent(data)         → ignored in v0.1 (logged debug)
        DoneEvent(finish_reason) → streaming=False; tool_activity=None; yield  (turn closed)
     except PrismalSDKError as e:
        → last message becomes kind="error" with a friendly text (§6)
        → retry affordance re-sends the same content on the same thread
```

Every `yield` is a Reflex `StateUpdate` pushed to the browser over the app's
WebSocket — the SDK's typed SSE events are translated 1:1 into UI state, and
nothing else. Long turns stay alive because each token yields an update
(app-level keepalive), mirroring the host's own SSE heartbeat design one hop
upstream.

### 4.2 Cancellation (stop button / tab close)

```
Stop clicked  → ChatState.stop_streaming(): sets a flag the async-for checks →
                breaks out of the iterator → SDK closes the HTTP response
                (SPEC-CSB-CHT-006) → host observes disconnect → cancels astream
                (SPEC-RHB-CHT-004) → no orphaned engine work.
Tab closed    → Reflex tears down the per-tab state; the in-flight handler is
                cancelled → same chain.
```

The webchat never sends an explicit cancel RPC — early stream closure **is**
the cancellation contract, end to end.

### 4.3 Embedding (RF-WCB-004)

```
host page:  <script src="https://chat.example.com/embed.js" async></script>
  └─ embed.js injects: launcher bubble (fixed, bottom-right)
        click → iframe src="https://chat.example.com/chat" (bare route)
        postMessage {type:"prismal-chat:open"|"close"} ⇄ page ↔ iframe
webchat responses carry:
  Content-Security-Policy: frame-ancestors <PRISMAL_WEBCHAT_EMBED_ORIGINS…>
  (empty list ⇒ 'self' — embedding disabled by default)
```

`/chat` renders the same `ChatState`-driven panel without page chrome. The
allowlist is enforced by the server header (CSP), not by JS checks — the
browser refuses to frame the chat from a non-allowed origin.

### 4.4 Configuration & secret path (RF-WCB-006)

```
env (PRISMAL_WEBCHAT_*) ──▶ WebchatSettings (pydantic-settings, backend import)
                              ├─ base_url, token (SecretStr), org_id ──▶ client.py → AsyncPrismalClient
                              └─ title, welcome, accent, theme, embed_origins ──▶ components (values only)
```

`WebchatSettings` is **never** an `rx.State` field and no handler copies the
token into state — state is serialized to the browser; settings are not. Only
derived, non-secret presentation values (title, colors, welcome text) cross
into components.

---

## 5. Architecture Decision Records

### ADR-001 — Reflex as the full-stack framework
**Decision:** Build the webchat as a Reflex application (Python compiles to a
React frontend + FastAPI backend, state synced over WebSocket).
**Rationale:** explicit stack decision for this repo; it keeps the whole
ecosystem Python-first, lets the webchat consume the **existing**
`prismal-sdk` instead of waiting on the deferred JS/TS SDK
(`CSB-FUTURE-03`), and its yield-per-update event handlers map naturally onto
the SDK's typed event stream (§4.1). **Alternatives:** Lit/React/Preact
widget in TypeScript (requires a JS SDK or hand-rolled SSE + CORS + token in
the browser — three problems the BFF design avoids); server-rendered
templates + htmx (weaker streaming ergonomics). **Consequences:** embedding
is iframe-based (ADR-003) and deployment is a Python service, not a static
bundle (ADR-006). **Status:** Accepted.

### ADR-002 — BFF: the browser never talks to `prismal-server`
**Decision:** All engine traffic flows browser → webchat backend →
(`prismal_sdk`) → `prismal-server`. The service bearer token lives only in
`WebchatSettings` (backend), never in state or page payloads.
**Rationale:** the host's auth contract is a single bearer credential
(`SPEC-RHB-SDK-003`) — meaningless to hand to anonymous visitors; a BFF keeps
the secret server-side, needs no `cors_origins` opening, and gives one narrow
place to add per-visitor identity later (WCB-FUTURE-03). **Alternatives:**
direct browser↔host SSE (token exposure or anonymous-only, CORS, JS SSE
parsing). **Status:** Accepted.

### ADR-003 — iframe + `embed.js` loader for embedding
**Decision:** Embedding = a static `embed.js` that injects a launcher bubble
and an iframe pointing at the bare `/chat` route; origin control via a
`frame-ancestors` CSP built from config. **Rationale:** a Reflex app is a
served application, not a distributable JS bundle — the iframe is the natural
embedding unit; CSP is the browser-enforced (not spoofable in-page) way to
restrict who may embed. **Alternatives:** web component (requires the
pure-JS widget path, deferred as WCB-FUTURE-05); popup window (worse UX).
**Status:** Accepted.

### ADR-004 — One thread per browser tab, engine owns history
**Decision:** `ChatState` (per-tab by Reflex design) lazily creates one
`thread_id` and reuses it for the tab's lifetime. The webchat persists
nothing; conversation history lives in the engine's checkpointer keyed by
that `thread_id` (`SPEC-RHB-THR-*`). **Rationale:** zero storage in the
webchat keeps it stateless-restartable and out of the engine's business;
"one tab = one conversation" matches user expectations for an embedded
widget. **Alternatives:** webchat-side DB of conversations (duplicates the
checkpointer; a dashboard concern). **Status:** Accepted.

### ADR-005 — Fake SDK client as the unit-test seam
**Decision:** Unit tests inject a `FakeAsyncPrismalClient` that replays
scripted event sequences (`TokenEvent…DoneEvent`, mid-stream
`PrismalAPIError`, transport errors); no Reflex frontend compile and no
network in the unit suite. **Rationale:** mirrors the engine's
factory-injection testing pattern and the SDK's own offline suite; the
webchat's testable surface is exactly "SDK events in → state transitions
out". **Status:** Accepted.

### ADR-006 — Single-process deploy in v0.1
**Decision:** v0.1 ships one container running the Reflex app; no sticky-
session/multi-worker story. **Rationale:** per-tab state lives in the app
process; distributed Reflex state (external store) is real work with no
current load to justify it — documented in `docs/deploy.md`, tracked as
WCB-FUTURE-06. **Status:** Accepted.

---

## 6. Error handling

- Every SDK exception is caught at exactly one place — the streaming handler
  in `ChatState` — and mapped to a visitor-friendly message plus a retry
  affordance. Nothing else in the app touches exceptions from transport.
- Mapping (visitor text is illustrative, finalized in the UI copy pass):
  `PrismalConnectionError` / `PrismalTimeoutError` → "Can't reach the
  assistant right now — try again."; `BudgetExceededError` → "The assistant
  is over capacity for now."; `PolicyDeniedError` / `PermissionDeniedError` →
  "That request can't be processed."; any other `PrismalAPIError` /
  `PrismalSDKError` → generic failure text. Codes, stack traces, and server
  messages go to the webchat's logs only — never rendered to the visitor
  (mirrors the host's own opaque-500 rule, `SPEC-RHB-ERR-002`).
- A mid-stream error leaves the partial assistant text in place, marks the
  message as errored, and re-enables input — the visitor never sees a frozen
  spinner.
- Retry re-sends the same content on the same `thread_id`; it is a **user
  action**, never automatic (the SDK already forbids auto-retrying chat
  turns, `SPEC-CSB-RSL-002` — the webchat honors the same rule one layer up).

---

## 7. Observability

The webchat is a thin host-side app: structured logs (turn started/finished,
`thread_id`, event counts, mapped error codes — never message content, never
the token) via standard `logging`. It does not stand up its own OTel stack in
v0.1; engine-side tracing (Langfuse/OTel) already covers the interesting
part of every turn. A request-id per turn correlates webchat logs with host
logs. Revisit if the webchat grows server fleet concerns (WCB-FUTURE-06).

---

## 8. Packaging & deploy (sketch)

`uv`-based project; `reflex run` for dev, Dockerfile for prod (single
container serving frontend + backend + WS; reverse-proxy note for WebSocket
upgrade in `docs/deploy.md`). Not published to PyPI — the webchat is a
deployable application, not a library. Versioning follows the org's
`MAJOR.MINOR.PATCH`; `v0.1.0` targets the M5 exit criterion in `PLAN.md`.
Pins: `reflex>=0.8,<0.9`, `prismal-sdk>=0.1,<1` (both bumped deliberately).

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-19 | Ernesto Crespo | Initial architecture: Reflex BFF over prismal-sdk, iframe embedding, per-tab threads |
