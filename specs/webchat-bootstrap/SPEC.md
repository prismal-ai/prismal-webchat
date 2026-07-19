# prismal-webchat — Technical Specification (WebChat Bootstrap)

| Field | Value |
|---|---|
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-07-19 |
| **Companion** | [`PLAN.md`](./PLAN.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`TASKS.md`](./TASKS.md) |

Requirement IDs are `SPEC-WCB-<AREA>-NNN`. Priority follows RFC 2119
(`MUST`/`SHOULD`/`MAY`). Each maps back to an `RF-WCB-*` in `PLAN.md`. Where a
requirement leans on a sibling contract, the sibling's ID is cited
(`SPEC-CSB-*` from `prismal-sdk`, `SPEC-RHB-*` from `prismal-server`).

---

## 1. Application & construction

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-APP-001 | The app MUST be a Reflex application exposing two routes: `/` (full chat page with chrome) and `/chat` (bare panel, iframe-safe), both driven by the same `ChatState`. | `MUST` |
| SPEC-WCB-APP-002 | The repo MUST NOT import `prismal` or `prismal_server`, and MUST NOT use `httpx` (or any HTTP client) directly against `prismal-server` — all upstream traffic goes through `prismal_sdk`. Enforced by an AST boundary-guard test. | `MUST` |
| SPEC-WCB-APP-003 | The SDK client MUST be a process-wide `AsyncPrismalClient` built lazily from `WebchatSettings` (`client.py::get_client()`), closed on app shutdown. | `MUST` |
| SPEC-WCB-APP-004 | A fresh clone MUST boot with zero configuration against a local default host (`http://localhost:8000`, no token — the SDK's dev defaults, `SPEC-CSB-TRN-005`/`AUT-001`). | `SHOULD` |

## 2. Chat & streaming

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-CHT-001 | On send, the handler MUST append the user message, clear the input, and yield before any network call (instant input feedback). | `MUST` |
| SPEC-WCB-CHT-002 | If the tab has no `thread_id`, the handler MUST call `create_thread()` once and reuse the returned `thread_id` for all subsequent turns in the tab (ADR-004). | `MUST` |
| SPEC-WCB-CHT-003 | The handler MUST consume `send_message()`'s typed events and yield a state update per event: `TokenEvent.delta` appends to the live assistant message; `ToolCallEvent.name` sets a visible tool-activity indicator; `DoneEvent` clears streaming state and the indicator. `StateEvent` MAY be ignored (logged at debug). | `MUST` |
| SPEC-WCB-CHT-004 | While a turn streams, the send affordance MUST be disabled and a stop affordance MUST be shown; at most one in-flight turn per tab. | `MUST` |
| SPEC-WCB-CHT-005 | Stop (or tab teardown) MUST break out of the event iterator promptly so the SDK closes the stream and the host cancels the run (`SPEC-CSB-CHT-006` → `SPEC-RHB-CHT-004`). No explicit cancel RPC is sent. | `MUST` |
| SPEC-WCB-CHT-006 | Visitor input MUST be passed to `send_message(content=…)` unmodified — no templating, prefixing, or prompt construction anywhere in this repo (`SPEC-CSB-CHT-007`; the engine's security layers apply server-side). | `MUST` |
| SPEC-WCB-CHT-007 | A configurable welcome message MUST render as the first assistant bubble without consuming a turn (purely presentational; not sent to the engine). | `SHOULD` |
| SPEC-WCB-CHT-008 | Assistant text SHOULD render markdown (code blocks, lists, links with `rel="noopener"`); raw HTML in model output MUST NOT be interpreted (rendered inert/escaped). | `SHOULD` |

## 3. Error UX

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-ERR-001 | Every `PrismalSDKError` raised during a turn MUST be caught in the streaming handler and rendered as an in-chat error bubble with visitor-friendly text (mapping table in `ARCHITECTURE.md` §6); input MUST be re-enabled. | `MUST` |
| SPEC-WCB-ERR-002 | Error codes, server messages, and stack traces MUST NOT be shown to the visitor; they go to webchat logs only (mirrors `SPEC-RHB-ERR-002`). | `MUST` |
| SPEC-WCB-ERR-003 | A mid-stream error MUST preserve the partial assistant text already rendered and mark the message as errored — never blank it or leave a spinner. | `MUST` |
| SPEC-WCB-ERR-004 | Retry MUST be a visitor action that re-sends the same content on the same `thread_id`; the webchat MUST NOT auto-retry a chat turn (`SPEC-CSB-RSL-002` honored one layer up). | `MUST` |

## 4. Embedding

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-EMB-001 | A static `embed.js` MUST be served by the app; adding one `<script src=".../embed.js" async>` tag to any page MUST inject a floating launcher bubble that toggles an iframe of `/chat`. | `MUST` |
| SPEC-WCB-EMB-002 | Responses for `/chat` (and `embed.js`) MUST carry a `Content-Security-Policy: frame-ancestors …` header built from `embed_origins` config; an empty list MUST yield `'self'` (embedding disabled by default). | `MUST` |
| SPEC-WCB-EMB-003 | The loader MUST support a minimal `postMessage` API — `{type:"prismal-chat:open"}` / `{type:"prismal-chat:close"}` — and MUST validate `event.origin` against the configured chat origin before acting. | `SHOULD` |
| SPEC-WCB-EMB-004 | `embed.js` MUST NOT contain any secret, org identifier, or `prismal-server` URL — it only knows the webchat's own origin. | `MUST` |
| SPEC-WCB-EMB-005 | A `demo.html` host page MUST exist in-repo for manual embedding verification (M4 exit). | `SHOULD` |

## 5. Auth, tenancy & secret hygiene

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-AUT-001 | The webchat authenticates to `prismal-server` with a single service credential from `WebchatSettings.token` (`SecretStr`), passed only to the SDK client constructor. Visitors are anonymous in v0.1. | `MUST` |
| SPEC-WCB-AUT-002 | The token MUST never appear in any `rx.State` field, event payload, compiled frontend asset, log line, or error message. A dedicated test MUST assert its absence from state serialization and compiled output. | `MUST` |
| SPEC-WCB-AUT-003 | When `org_id` is configured it MUST be applied client-wide via the SDK (`X-Org-Id`, `SPEC-CSB-AUT-002`); the webchat MUST NOT invent any other header or tenancy mechanism. | `MUST` |

## 6. Configuration

`WebchatSettings` (pydantic-settings, prefix `PRISMAL_WEBCHAT_`) is
backend-only (never state, ADR-002/§4.4).

| Key | Env var | Default | Meaning |
|---|---|---|---|
| `server_url` | `PRISMAL_WEBCHAT_SERVER_URL` | `http://localhost:8000` | Target `prismal-server` |
| `token` | `PRISMAL_WEBCHAT_TOKEN` | `None` | Service bearer credential (`SecretStr`) |
| `org_id` | `PRISMAL_WEBCHAT_ORG_ID` | `None` | Tenant for all webchat traffic |
| `title` | `PRISMAL_WEBCHAT_TITLE` | `"prismal"` | Widget/page title |
| `welcome_message` | `PRISMAL_WEBCHAT_WELCOME_MESSAGE` | `"Hi! How can I help?"` | First assistant bubble (presentational) |
| `accent_color` | `PRISMAL_WEBCHAT_ACCENT_COLOR` | `"#6C5CE7"` | Accent for bubbles/launcher |
| `theme` | `PRISMAL_WEBCHAT_THEME` | `"light"` | `light` \| `dark` \| `auto` |
| `embed_origins` | `PRISMAL_WEBCHAT_EMBED_ORIGINS` | `[]` | Allowed `frame-ancestors`; empty ⇒ `'self'` |

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-CFG-001 | `server_url` MUST be validated as an absolute `http(s)://` URL at startup, failing fast. | `MUST` |
| SPEC-WCB-CFG-002 | `theme` MUST be validated against `{light, dark, auto}` and `embed_origins` entries against origin syntax (`scheme://host[:port]`, no path) at startup. | `MUST` |
| SPEC-WCB-CFG-003 | Only derived, non-secret presentation values (title, welcome, colors) may cross into components/state; settings objects themselves MUST NOT. | `MUST` |

## 7. Non-functional

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-NFR-001 | The unit suite MUST run with no network and no Reflex frontend compile, using a `FakeAsyncPrismalClient` that replays scripted event streams (ADR-005); a separate opt-in `contract` suite exercises a live `prismal-server`. | `MUST` |
| SPEC-WCB-NFR-002 | `ruff check .` and `mypy` on `prismal_webchat/` MUST be clean in CI. | `MUST` |
| SPEC-WCB-NFR-003 | Logs MUST NOT contain message content or the token; they MAY contain `thread_id`, event counts, mapped error codes, and a per-turn request id. | `MUST` |
| SPEC-WCB-NFR-004 | The chat panel SHOULD meet basic a11y: keyboard send (Enter), focus management after send/error, ARIA live region for streaming assistant text. | `SHOULD` |
| SPEC-WCB-NFR-005 | Version pins: `reflex>=0.8,<0.9`, `prismal-sdk>=0.1,<1`; bumps are deliberate PRs, not drive-by. | `MUST` |

---

## 8. Traceability (RF → SPEC)

| RF | Covered by |
|---|---|
| RF-WCB-001 | SPEC-WCB-APP-001, SPEC-WCB-CHT-001/007 |
| RF-WCB-002 | SPEC-WCB-CHT-003/004/008 |
| RF-WCB-003 | SPEC-WCB-CHT-002/005 |
| RF-WCB-004 | SPEC-WCB-EMB-001..005 |
| RF-WCB-005 | SPEC-WCB-APP-002/003, SPEC-WCB-CHT-006 |
| RF-WCB-006 | SPEC-WCB-AUT-001..003, SPEC-WCB-CFG-001..003 |
| RF-WCB-007 | SPEC-WCB-ERR-001..004 |
| RF-WCB-008 | SPEC-WCB-CFG table (title/welcome/accent/theme) |
| RF-WCB-009 | SPEC-WCB-NFR-001 |

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-19 | Ernesto Crespo | Initial technical spec for the embeddable webchat |
