# prismal-webchat — Task Breakdown (WebChat Bootstrap)

| Field | Value |
|---|---|
| **Status** | `IMPLEMENTED` — `0.1.0` (released from `main` by `release.yml`; see `DELTA-2026-11-pypi.md`) |
| **Version** | 1.0 |
| **Date** | 2026-07-19 |
| **Companion** | [`PLAN.md`](./PLAN.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`SPEC.md`](./SPEC.md) |

Status legend: `TODO` · `WIP` · `DONE` · `BLOCKED`. Every task is **test-first
(TDD)** — write the failing test, watch it fail, minimal code to green. Tasks
map to `SPEC-WCB-*` IDs and the `M0…M5` milestones in `PLAN.md`.

---

## Phase 0 — Seed & scaffold (M0/M1)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-00-01 | SDD set (`PLAN`/`ARCHITECTURE`/`SPEC`/`TASKS`) + `CLAUDE.md` + `README.md` | 0.5 d | — | — | `DONE` |
| WCB-00-02 | `pyproject.toml` (`reflex>=0.8,<0.9`, `prismal-sdk>=0.1,<1`; dev extras `pytest`, `pytest-asyncio`, `ruff`, `mypy`) + `rxconfig.py`; `reflex run` boots an empty page | 0.4 d | 00-01 | NFR-005 | `DONE` (`b1a9c4f`) |
| WCB-00-03 | `settings.py`: `WebchatSettings` (prefix, `SecretStr` token, URL/theme/origin validation, fail-fast) | 0.4 d | 00-02 | CFG-001/002, AUT-001 | `DONE` (`0a5f7ab`) |
| WCB-00-04 | Boundary-guard test: AST scan — no `prismal`/`prismal_server` import, no direct `httpx` use in `prismal_webchat/` | 0.2 d | 00-02 | APP-002 | `DONE` (`0a5f7ab`) |
| WCB-00-05 | `tests/conftest.py`: `FakeAsyncPrismalClient` replaying scripted event streams + settings fixtures (offline) | 0.4 d | 00-02 | NFR-001 | `DONE` (`0a5f7ab`) |
| WCB-00-06 | CI (`.github/workflows/ci.yml`): ruff + mypy + pytest (unit); opt-in `contract` job | 0.3 d | 00-02 | NFR-002 | `DONE` (DELTA-2026-11-pypi) |

## Phase 1 — Chat core (M2)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-01-01 | `client.py`: lazy process-wide `AsyncPrismalClient` from settings; closed on shutdown | 0.3 d | 00-03 | APP-003 | `DONE` (`18cd400`) |
| WCB-01-02 | `state/models.py`: `ChatMessage(role, text, kind)`, `ToolActivity` | 0.2 d | 00-02 | — | `DONE` (`18cd400`) |
| WCB-01-03 | `ChatState.send()`: append user msg + clear input + yield; lazy `create_thread()`; thread reuse | 0.5 d | 01-01, 01-02, 00-05 | CHT-001/002 | `DONE` (`18cd400`) |
| WCB-01-04 | Streaming loop: token append / tool indicator / done, one yield per event; single in-flight turn | 0.7 d | 01-03 | CHT-003/004 | `DONE` (`18cd400`) |
| WCB-01-05 | Stop + tab-teardown cancellation (break iterator → SDK closes stream) | 0.4 d | 01-04 | CHT-005 | `DONE` (`18cd400`) |
| WCB-01-06 | Pass-through content test: input reaches `send_message` unmodified | 0.2 d | 01-03 | CHT-006 | `DONE` (`18cd400`) |

## Phase 2 — Chat UX (M3)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-02-01 | `components/`: `chat_panel`, `input_bar` — bubbles, tool-activity chip, disabled-while-streaming | 0.6 d | 01-04 | CHT-004 | `DONE` (`e51bc66`) |
| WCB-02-02 | Error mapping table → in-chat error bubble + retry (same content, same thread); partial text preserved | 0.5 d | 01-04 | ERR-001..004 | `DONE` (`e51bc66`) |
| WCB-02-03 | Welcome message (presentational, not sent to engine) | 0.2 d | 02-01 | CHT-007 | `DONE` (`e51bc66`) |
| WCB-02-04 | Markdown rendering, inert HTML, `rel="noopener"` links | 0.4 d | 02-01 | CHT-008 | `DONE` (`e51bc66`) |
| WCB-02-05 | `theme.py`: light/dark/auto + accent from settings; only non-secret values cross into components | 0.3 d | 00-03 | CFG-003 | `DONE` (`e51bc66`) |
| WCB-02-06 | A11y pass: Enter-to-send, focus management, ARIA live region | 0.3 d | 02-01 | NFR-004 | `DONE` (`e51bc66`) |

## Phase 3 — Embedding (M4)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-03-01 | `/chat` bare route (no chrome, iframe-safe) sharing `ChatState` | 0.3 d | 02-01 | APP-001 | `DONE` (`36153d1`) |
| WCB-03-02 | `embed.js`: launcher bubble + iframe injection; no secrets/URLs beyond the webchat origin | 0.5 d | 03-01 | EMB-001/004 | `DONE` (`36153d1`) |
| WCB-03-03 | `frame-ancestors` CSP from `embed_origins` (empty ⇒ `'self'`) on `/chat` + `embed.js` | 0.4 d | 03-01 | EMB-002 | `DONE` (`36153d1`) |
| WCB-03-04 | `postMessage` open/close with origin validation | 0.3 d | 03-02 | EMB-003 | `DONE` (`36153d1`) |
| WCB-03-05 | `embed/demo.html` + manual verification checklist (allowed origin opens; disallowed blocked) | 0.2 d | 03-02, 03-03 | EMB-005 | `DONE` (`36153d1`) |

## Phase 4 — Hardening & release (M5)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-04-01 | Secret-leak test: token absent from state serialization, compiled frontend, logs | 0.4 d | 01-01, 02-01 | AUT-002, NFR-003 | `DONE` (`b0db384`) |
| WCB-04-02 | `tests/contract/`: opt-in suite vs a running `prismal-server` — one streamed turn, thread reuse, error path | 0.5 d | all | NFR-001 | `DONE` (`b0db384`) |
| WCB-04-03 | Dockerfile + `docs/deploy.md` (WS reverse-proxy note, single-process caveat) | 0.5 d | 03-* | — | `DONE` (DELTA-2026-11-pypi) |
| WCB-04-04 | `docs/embedding.md` + `docs/configuration.md` | 0.3 d | 03-*, 00-03 | — | `DONE` (`b0db384`) |
| WCB-04-05 | `ruff` + `mypy` clean; coverage baseline recorded | 0.3 d | all | NFR-002 | `DONE` (`b0db384`) |
| WCB-04-06 | Tag `v0.1.0`; release workflow (GHCR image optional) | 0.2 d | 04-01..05 | — | `DONE` — `v0.1.0` tagged by `release.yml` on merge |

## Future (out of scope for v0.1, tracked only)

| ID | Task | Trigger |
|---|---|---|
| WCB-FUTURE-01 | WebSocket transport to the host | `prismal-server` ships WS + `prismal-sdk` `CSB-FUTURE-01` lands — **trigger met** (host 0.2+, SDK `client.ws()`); deferred past 0.1.0 (DELTA-2026-11-pypi §4) |
| WCB-FUTURE-02 | Multi-conversation history UI (list/resume threads) | Real demand; likely shared with `prismal-dashboard` |
| WCB-FUTURE-03 | Per-visitor identity (login → per-user `org_id`/budget) | A deployment needs per-user tenancy/limits |
| WCB-FUTURE-04 | File/media upload to the multimodal layer | Host specs a media upload route |
| WCB-FUTURE-05 | Pure-JS standalone widget (no Python backend) | JS/TS SDK exists (`CSB-FUTURE-03` in `prismal-sdk`) |
| WCB-FUTURE-06 | Multi-worker deploy (external Reflex state, sticky WS) | Real load on a production deployment |
| WCB-FUTURE-07 | AG-UI interrupt resume UI (`run_agui(resume=…)`, SDK 0.3) | A deployment enables human-in-the-loop interrupts |

---

## Definition of Done (v0.1)

- `uv pip install -e ".[dev]"` + `reflex run` works from a fresh clone;
  `ruff check .` and `mypy prismal_webchat` are clean.
- A visitor sends a message and watches the answer stream token-by-token,
  sees tool activity, can stop mid-turn, and gets a friendly retryable error
  bubble on failure — all verified offline against `FakeAsyncPrismalClient`.
- One `thread_id` per tab, minted lazily, reused across turns; nothing
  persisted webchat-side.
- `demo.html` embeds the widget via `embed.js` from an allowed origin; a
  disallowed origin is blocked by CSP.
- The boundary-guard test proves no `prismal`/`prismal_server` import and no
  direct HTTP use; the secret-leak test proves the token never reaches the
  browser.
- The `contract` suite passes against a locally running `prismal-server`.
- One-container Docker deploy chats end-to-end against a live host.

## Estimate roll-up

~**10 person-days** across M1–M5 (excludes the M0 seed). Critical path is
Phase 0 → 1 → 2 → 3 (scaffold before chat core before UX before embedding);
Phase 4 closes. Reconciled 2026-11-03 against the commits on `feat/wcb-00-scaffold-uv`: 26/29
`DONE`; the last three (WCB-00-06, WCB-04-03, WCB-04-06) closed 2026-11-03 once
`prismal-ai-sdk` 0.3.0 reached PyPI (DELTA-2026-11-pypi): 29/29 `DONE`.

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-19 | Ernesto Crespo | Initial task breakdown for the embeddable webchat |
| 1.1 | 2026-11-03 | Ernesto Crespo | Statuses reconciled with the code (29/29 `DONE`); WCB-FUTURE-01 trigger met but deferred; WCB-FUTURE-07 added (DELTA-2026-11-pypi) |
