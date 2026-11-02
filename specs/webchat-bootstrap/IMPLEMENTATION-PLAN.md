# prismal-webchat — Implementation Plan (phases & tasks)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `ACTIVE` |
| **Version** | 1.2 |
| **Date** | 2026-11-02 |
| **Inputs** | [`PLAN.md`](./PLAN.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`SPEC.md`](./SPEC.md) · [`TASKS.md`](./TASKS.md) · [`DELTA-2026-10-usage-agui.md`](./DELTA-2026-10-usage-agui.md) · [`DELTA-2026-11-uv-silverpoint.md`](./DELTA-2026-11-uv-silverpoint.md) |
| **Target** | `v0.1.0` (bootstrap + the 2026-10 delta folded in, as that delta states) |

This document consolidates the SDD set into **one executable sequence**: the
`WCB-00…04` tasks of `TASKS.md`, the `WCB-D-*` tasks of the 2026-10 delta,
and the `WCB-S-*` tasks introduced by the 2026-11 stack delta (uv +
`reflex-silverpoint-react`). Task IDs from the source artifacts are kept so
traceability to `SPEC-WCB-*` is unchanged; where a delta task modifies an
original task, the two are merged and both IDs are listed.

Every task is **TDD** (failing test → minimal code → green) and must pass the
`CLAUDE.md` review checklist.

---

## 1. Repository analysis (as of 2026-11-02)

| Item | Finding | Consequence |
|---|---|---|
| Code | None. Repo holds only `CLAUDE.md`, `README.md`, `LICENSE`, `.gitignore`, `specs/`. | Everything from `WCB-00-02` onward is `TODO`. |
| `prismal-sdk` | **Not on PyPI.** Sibling checkout at `../prismal-sdk`, version `0.2.0.dev0`, exports `AsyncPrismalClient`, classic events (`TokenEvent`, `ToolCallEvent`, `StateEvent`, `DoneEvent`, `Usage`), AG-UI (`prismal_sdk.agui`: `AgUiEvent`, `RunFinished`, `PrismalUsageEvent`, …) and the full exception set (`BudgetExceededError`, `ProtocolNotEnabledError`, …). | Resolve via a **uv source** (path for dev, git tag for CI/Docker). Delta 2026-10's `>=0.2,<1` floor is satisfiable only by the dev pre-release today. |
| `reflex` | PyPI latest `0.10.1` (requires Python `>=3.11`). | — |
| `reflex-silverpoint-react` | PyPI latest `0.9.1` (wraps `@silverpoint/react`), **requires `reflex>=0.10.0`**, Python `>=3.11`. | **Conflicts** with `SPEC-WCB-NFR-005` (`reflex>=0.8,<0.9`) → pin change in DELTA-2026-11. |
| silverpoint chat component | **No dedicated chat/message component exists** in the catalog (0.9.2: 38 UI/composed/overlay components + charts). | The chat panel is **composed** from silverpoint primitives (§3). Markdown rendering stays with Reflex's `rx.markdown`. |
| Package manager | `uv 0.11.7` installed locally. | All commands below use `uv` (`uv sync`, `uv run`, `uv lock`); `uv.lock` is committed. |

### Decisions (2026-11-02)

1. **DELTA-2026-11 accepted** — `reflex>=0.10,<0.11`, silverpoint as the UI kit.
2. **`prismal-sdk` from PyPI** — wait for the SDK to be published. Until then
   `[tool.uv.sources]` resolves the sibling checkout `../prismal-sdk` for local
   dev; **WCB-00-06 (CI) and WCB-04-03 (Docker) are `BLOCKED`** on that release.
   Unblocking = delete the `[tool.uv.sources]` entry and `uv lock`.

### Findings for WCB-D-01

- DELTA-2026-10 names the sub-agent key `subagent_id`; the SDK (`prismal_sdk.agui.SubagentStarted/Finished`) exposes **`subagent_run_id`**. The widget follows the SDK; `docs/agui.md` must record the real field.
- `budget_exceeded` fixture pinned in `tests/scripts.py::budget_exceeded` (402, `scope`/`limit`/`consumed` details, built via `error_for_code`).

### Findings for Phase 3 (feed WCB-04-03/04 docs)

- `embed.js` lives in `assets/` (Reflex serves it at `/embed.js`), not `prismal_webchat/embed/` as ARCHITECTURE §3 sketched; `demo.html` stays in `prismal_webchat/embed/`.
- The CSP header only exists where the Python backend serves the page: **prod `--single-port`** (and Docker). `reflex run` dev serves the frontend from Vite on :3000 without it — embedding policy must be verified in prod mode.
- Prod single-port needs equal ports: `reflex run --env prod --single-port --frontend-port 8001 --backend-port 8001` (rxconfig keeps 3000/8001 for dev).
- `/chat` answers `307 → /chat/`; `embed.js` points at `/chat` and the redirect carries the CSP too.
- `'self'` is always in `frame-ancestors`; the allowlist is appended.
- Prod builds showed Reflex's "Built with Reflex" badge bottom-right, overlapping the widget's Send button; disabled with `show_built_with_reflex=False` (owner decision 2026-11-02, verified in a prod build).

### Progress

| Task | Status | Notes |
|---|---|---|
| WCB-00-02 | `DONE` | `pyproject.toml` (pins + `package = false`), `uv.lock`, `reflex.lock/` (npm), `rxconfig.py` (`app_module_import`, frontend `:3000`, backend `:8001`), `prismal_webchat/webchat.py`; tests `test_dependencies.py`, `test_app_skeleton.py` |
| WCB-00-03 + D-03 | `DONE` | `prismal_webchat/settings.py` (frozen, `SecretStr` token, URL/theme/origin validation, `agui_enabled`/`show_usage`); `pydantic-settings` now a direct dep |
| WCB-00-04 | `DONE` | `tests/boundary.py` AST scanner (static, `from x import y`, `importlib`/`__import__` literals; httpx/requests/aiohttp/urllib3/urllib.request/http.client) + `test_boundary.py` |
| WCB-00-05 + D-02 | `DONE` | `tests/fakes.py` (`FakeAsyncPrismalClient`: raise-in-place, early-close tracking, verbatim `sent`), `tests/scripts.py` (classic + AG-UI via SDK `parse_agui_event` / `error_for_code`), `tests/conftest.py` |
| WCB-00-06 | `BLOCKED` | Waiting for `prismal-sdk` on PyPI |
| WCB-04-01 + D-08 (scan) | `DONE` | `tests/unit/test_secret_hygiene.py` (Reflex-serialized state after classic + AG-UI turns with full usage, backend vars, DEBUG logs; mutation-checked) + opt-in `tests/compiled/` (`uv run pytest -m compile`: real `reflex compile` with sentinel env, positive control on the welcome text) |
| WCB-04-02 + D-09 | `DONE` | `tests/contract/test_live_server.py` (`uv run pytest -m contract`): classic chunks, thread reuse, `/tool` chip, `/error` bubble, AG-UI text + `PrismalUsageEvent` hidden, AG-UI chip by call id, opt-in footer = 15 — 7/7 green vs prismal-server fake-LLM + `PRISMAL_AGUI_EVENTS_ENABLED=true` |
| WCB-04-04 + D-01 (doc) | `DONE` | `docs/configuration.md`, `docs/embedding.md`, `docs/agui.md`; README/CLAUDE.md updated |
| WCB-04-05 | `DONE` | ruff + mypy strict clean; coverage baseline **99 %** (450 stmts, 1 defensive line uncovered) |
| WCB-04-06 | `BLOCKED` | `v0.1.0` tag after WCB-00-06/04-03 |
| WCB-01-01 | `DONE` | `client.py`: lazy process-wide client, `client_lifespan` registered on the app (closes at shutdown), sticky AG-UI fallback flag |
| WCB-01-02 | `DONE` | `state/models.py`: `ChatMessage`, `ToolActivity`, `ChatView` protocol |
| WCB-01-03…06 | `DONE` | `state/chat.py`: `send` (regular) → `stream_turn` (**background**, so Stop is processed mid-turn); one `async with self` per event; Stop cancels the in-flight task → `aclosing` unwinds the SDK stream; tab teardown re-raises `CancelledError`; content verbatim via backend-only `_pending_content` |
| WCB-D-04 | `DONE` | `state/mapping.py` (classic) + `state/agui_mapper.py`; table-driven tests incl. interleaving, nested sub-agents (`subagent_run_id`), ignored/unknown events |
| WCB-D-05 | `DONE` | AG-UI behind `agui_enabled`; `ProtocolNotEnabledError` → one classic resend, sticky per process |
| WCB-02-01…06, S-02, S-03, D-06, D-07, D-08 (UI) | `DONE` | `components/theme.py` (light silverpoint+accent / dark cyanotype / auto via `color_mode_cond`, fail-fast contrast), `components/chat_panel.py` (bubbles seeded by id, skeleton, chips, sub-agent line, `sp_alert`+Retry, opt-in token footer, `role=log` + `aria-live`), `components/input_bar.py` (`sp_input` form, Send/Stop, focus after send), `ChatState.retry` (one per failure, never automatic) |
| WCB-03-01…05 | `DONE` | `/chat` bare route (same `ChatState`, in-chat Close → `postMessage`); `embedding.py` ASGI middleware via `api_transformer` adds `frame-ancestors 'self' <origins>` to **every** response (kept alongside any existing CSP); `assets/embed.js` derives its origin from `document.currentScript` (no config, no URL/secret), lazy iframe, `aria-expanded`, Escape, `window.PrismalChat`, `event.origin` check; `prismal_webchat/embed/demo.html` + checklist. Verified in headless Chrome (prod single-port): allowed origin opens and chats, in-chat Close works, forged same-page message ignored, other origin refused by CSP |
| WCB-S-01 | `DONE` | Verified in headless Chrome against `prismal-server` fake-LLM mode: live token streaming, input clears + keeps focus, `/error` → friendly bubble + Retry, raw HTML inert, links `noopener`, no server URL in page, dark theme renders |
| WCB-04-03 | `BLOCKED` | Same |

---

## 2. Toolchain (uv)

```toml
# pyproject.toml (excerpt — produced by WCB-00-02)
[project]
name = "prismal-webchat"
requires-python = ">=3.11"
dependencies = [
  "reflex>=0.10,<0.11",                  # DELTA-2026-11 (was >=0.8,<0.9)
  "reflex-silverpoint-react>=0.9.1,<0.10",
  "prismal-sdk>=0.2.0.dev0,<1",          # DELTA-2026-10 floor; dev pre-release until 0.2.0 ships
  "pydantic-settings>=2.5",
]

[dependency-groups]
dev = ["pytest", "pytest-asyncio", "ruff", "mypy"]

[tool.uv.sources]
# Until prismal-sdk is on PyPI: sibling checkout for local dev (remove after release).
prismal-sdk = { path = "../prismal-sdk", editable = true }
```

Standard commands (replace the `uv pip install -e ".[dev]"` lines in
`README.md`/`CLAUDE.md` in WCB-04-04):

```bash
uv sync                          # create .venv from uv.lock (dev group included)
uv run reflex run                # dev server (frontend :3000, backend :8001)
uv run pytest                    # unit, offline
uv run pytest -m contract        # opt-in, live prismal-server
uv run ruff check . && uv run ruff format --check .
uv run mypy prismal_webchat
```

---

## 3. Chat UI composition with `reflex-silverpoint-react`

No `sp_chat` exists, so `components/` builds the chat from these builders
(all imported from the package root, snake_case props, values not DOM events):

| Chat element | Builder(s) | Notes / SPEC |
|---|---|---|
| Theme root | `silverpoint_provider(ground=…, substrate=…, mode=…, palette=…)` | Wraps `/` and `/chat`; values derived from settings only (`CFG-003`). Accent → `palette`; validated at startup with `check_palette`/`contrast_ratio`. |
| Message bubble | `sp_surface(frame="card", tone=…)` + `sp_avatar` (initials) | User vs. assistant differ by `tone` (silverpoint is monochrome by design — tone, not colour). Stable `id`/`seed` per message → deterministic hand-inked frame. |
| Assistant text | `rx.markdown` inside the bubble | Inert HTML, `rel="noopener"` links (`CHT-008`). |
| Streaming placeholder | `sp_skeleton` | Until the first `TokenEvent`/`TextMessageContent`. |
| Tool-activity chip | `sp_tag(tone=…)` + `sp_glyph` (tick when done) | Classic: one chip from `ToolCallEvent.name` (`CHT-003`). AG-UI: one chip per `tool_call_id`, running → done (`AGU-003`). |
| Sub-agent progress line | `sp_progress` (indeterminate line) + text | "working on: <name>" / "working…" (`AGU-004`). |
| Error bubble | `sp_alert(kind="error", title=…)` + `sp_button("Retry")` | Friendly copy only (`ERR-001/002`); no retry for `budget_exceeded` (DELTA-10 `ERR-002`). |
| Usage footer (opt-in) | muted `rx.text` / `sp_tag` | Only when `show_usage=True`; `total_tokens` only (`USG-002`). |
| Input | `sp_input(value=…, on_change=…, label=…)` inside `rx.el.form(on_submit=…)` | Controlled; Enter submits natively (`NFR-004`; `sp_textarea` has no key events — DELTA-2026-11 v1.2). |
| Send / Stop | `sp_button` (`primary`) / `sp_button` (`danger`) | Send disabled while streaming; Stop shown (`CHT-004`). |
| Welcome bubble | same bubble component, presentational | Not sent to the engine (`CHT-007`). |

The `embed.js` launcher bubble is **plain JS/CSS** (it runs on the host page,
outside Reflex); silverpoint styles exist only inside the iframe.

---

## 4. Phases & tasks

Legend: `Est.` in person-days · `Dep` = task IDs · `SPEC` = `SPEC-WCB-*` suffix.

### Phase 0 — Scaffold & foundations (M1)

Exit: `uv run reflex run` serves an empty silverpoint-themed page; guards,
settings and fake client green in CI.

| ID | Task | Est. | Dep | SPEC |
|---|---|---|---|---|
| WCB-D-01 | **Verify before build**: pin the `budget_exceeded` fixture (RH2 §11 / CS2 §7); write `docs/agui.md` (CS2 class → widget effect) | 0.2 | — | ERR-002, AGU-* |
| WCB-S-01 | Accept DELTA-2026-11; spike: `uv run reflex init` with `reflex 0.10.x` + `reflex-silverpoint-react 0.9.1`, render `sp_surface`/`sp_textarea` inside `silverpoint_provider`; confirm Python 3.13 works | 0.3 | — | NFR-005′, UI-001 |
| WCB-00-02 + D-02(pin) | `uv init` → `pyproject.toml` (§2), `[tool.uv.sources]` for `prismal-sdk`, `dependency-groups.dev`, `rxconfig.py`, committed `uv.lock`; dependency test asserts pins (`reflex>=0.10,<0.11`, `prismal-sdk>=0.2`) | 0.4 | S-01 | NFR-005′ |
| WCB-00-03 + D-03 | `settings.py`: `WebchatSettings` (prefix `PRISMAL_WEBCHAT_`, `SecretStr` token, URL/theme/origin validation, fail-fast) **plus** `agui_enabled`, `show_usage` (both `False`) | 0.5 | 00-02 | CFG-001/002/004, AUT-001 |
| WCB-00-04 | AST boundary guard: no `prismal`/`prismal_server` import, no direct `httpx` in `prismal_webchat/` | 0.2 | 00-02 | APP-002 |
| WCB-00-05 + D-02(fake) | `tests/conftest.py`: `FakeAsyncPrismalClient` with classic scripts **and** `protocol="ag-ui"` scripts (CS2 classes, raised `RunError` mapping, `ProtocolNotEnabledError`, `DoneEvent.usage`) + settings fixtures | 0.6 | 00-02 | NFR-001 |
| WCB-00-06 | CI (`.github/workflows/ci.yml`) on `astral-sh/setup-uv`: `uv sync --locked`, ruff, mypy, pytest unit; opt-in `contract` job; SDK via git source (open decision 2) | 0.3 | 00-02 | NFR-002 |

### Phase 1 — Chat core, classic + AG-UI (M2)

Exit: a full streamed turn (classic and AG-UI) passes offline against the fake
client: tokens append, done closes, error renders, stop cancels.

| ID | Task | Est. | Dep | SPEC |
|---|---|---|---|---|
| WCB-01-01 | `client.py`: lazy process-wide `AsyncPrismalClient`, `org_id` client-wide, closed on shutdown | 0.3 | 00-03 | APP-003, AUT-003 |
| WCB-01-02 | `state/models.py`: `ChatMessage(role, text, kind)`, `ToolActivity(id, name, status)`, sub-agent line model | 0.2 | 00-02 | — |
| WCB-01-03 | `ChatState.send()`: append user msg, clear input, yield; lazy `create_thread()`, reuse per tab | 0.5 | 01-01, 01-02, 00-05 | CHT-001/002 |
| WCB-01-04 | Classic streaming loop: one yield per event; token / tool / done; single in-flight turn | 0.7 | 01-03 | CHT-003/004 |
| WCB-01-05 | Stop + tab-teardown cancellation (break iterator; no cancel RPC) | 0.4 | 01-04 | CHT-005 |
| WCB-01-06 | Pass-through test: input reaches `send_message(content=…)` unmodified | 0.2 | 01-03 | CHT-006 |
| WCB-D-04 | `state/agui_mapper.py`: pure `AgUiEvent` → state mutation by `isinstance` (text, tool chip by `tool_call_id`, sub-agent by `subagent_id`, run end, ignore state/unknown); table-driven + interleaving tests | 0.7 | 00-05, 01-02 | AGU-002…007 |
| WCB-D-05 | Wire mapper into `send()` behind `agui_enabled`; `ProtocolNotEnabledError` → one resend classic, sticky for the process, logged once; flag-off snapshot test | 0.4 | 00-03, D-04, 01-04 | AGU-001/008, CHT-003 |

### Phase 2 — Chat UX with silverpoint (M3)

Exit: all `CHT-*`, `ERR-*`, `AGU-003/004`, `USG-*` green offline; panel
rendered with silverpoint components (§3).

| ID | Task | Est. | Dep | SPEC |
|---|---|---|---|---|
| WCB-02-05 + S-02 | `components/theme.py`: settings → `silverpoint_provider` args (light/dark/auto → ground/substrate/mode; accent → palette); `check_palette` contrast check at startup; only non-secret values cross | 0.4 | 00-03, S-01 | CFG-003, UI-002 |
| WCB-02-01 + S-03 | `components/chat_panel.py` (bubbles `sp_surface`+`sp_avatar`, `rx.markdown`, `sp_skeleton`, tool chip `sp_tag`) and `components/input_bar.py` (`sp_textarea`, `sp_button` send/stop, disabled while streaming) | 0.8 | 01-04, 02-05 | CHT-004, UI-001 |
| WCB-02-02 + D-07 | Error mapping → `sp_alert(kind="error")` + retry (same content, same thread), partial text kept; `budget_exceeded` row with no-retry copy; `ProtocolNotEnabledError` handled by D-05 | 0.6 | 01-04, 02-01 | ERR-001…004 |
| WCB-02-03 | Welcome bubble (presentational, never sent) | 0.2 | 02-01 | CHT-007 |
| WCB-02-04 | Markdown hardening: inert raw HTML, `rel="noopener"` links | 0.4 | 02-01 | CHT-008 |
| WCB-D-06 | Sub-agent line (`sp_progress` indeterminate) + per-call tool chip states; a11y live region | 0.4 | D-04, 02-01 | AGU-003/004 |
| WCB-D-08 (UI) | Usage policy: nothing usage-related in `rx.State` when `show_usage=False`; optional `total_tokens` footer; fail-open on missing usage | 0.3 | 00-03, 02-01 | USG-001…003 |
| WCB-02-06 | A11y: Enter-to-send on `sp_textarea`, focus after send/error, ARIA live region for streaming text | 0.3 | 02-01 | NFR-004 |

### Phase 3 — Embedding (M4)

Exit: `demo.html` opens the widget from an allowed origin; disallowed origin
blocked by CSP.

| ID | Task | Est. | Dep | SPEC |
|---|---|---|---|---|
| WCB-03-01 | `/chat` bare route (no chrome) sharing `ChatState` and the silverpoint provider | 0.3 | 02-01 | APP-001 |
| WCB-03-02 | `embed/embed.js`: plain-JS launcher + iframe; only knows the webchat origin | 0.5 | 03-01 | EMB-001/004 |
| WCB-03-03 | `frame-ancestors` CSP from `embed_origins` (empty ⇒ `'self'`) on `/chat` and `embed.js` | 0.4 | 03-01 | EMB-002 |
| WCB-03-04 | `postMessage` open/close with `event.origin` validation | 0.3 | 03-02 | EMB-003 |
| WCB-03-05 | `embed/demo.html` + manual checklist (allowed opens / disallowed blocked) | 0.2 | 03-02, 03-03 | EMB-005 |

### Phase 4 — Hardening & release (M5)

Exit: CI green; one-container deploy chats against live `prismal-server` 0.2;
tag `v0.1.0`.

| ID | Task | Est. | Dep | SPEC |
|---|---|---|---|---|
| WCB-04-01 + D-08 (scan) | Secret-leak + privacy scan: token and usage keys (`cost_usd`, `served_model`, `gateway`, `*_tokens`) absent from serialized state, compiled `.web/`, logs | 0.5 | 01-01, 02-01, D-08 | AUT-002, NFR-003, USG-001 |
| WCB-04-02 + D-09 | `tests/contract/` vs `prismal-server` 0.2 (`host_fake_llm_mode`): classic turn, thread reuse, AG-UI turn (`/tool` → chip, `PrismalUsageEvent`), `/error` → error bubble | 0.7 | Phases 1–3 | NFR-001, AGU-001/003/006 |
| WCB-04-03 | Dockerfile on `ghcr.io/astral-sh/uv` (`uv sync --frozen --no-dev`, `reflex export`/prod run) + `docs/deploy.md` (WS proxy, single process) | 0.5 | 03-* | — |
| WCB-04-04 | `docs/embedding.md`, `docs/configuration.md` (incl. `AGUI_ENABLED`, `SHOW_USAGE`); switch `README.md`/`CLAUDE.md` commands to `uv sync`/`uv run` and the new reflex pin | 0.3 | 03-*, 00-03 | — |
| WCB-04-05 | `ruff` + `mypy` clean; coverage baseline | 0.3 | all | NFR-002 |
| WCB-04-06 | Tag `v0.1.0`; release workflow (GHCR image optional) | 0.2 | 04-01…05 | — |

---

## 5. Critical path & estimate

```
D-01 ─┐
S-01 ─┴─▶ 00-02 ─▶ 00-03 ─▶ 01-01 ─▶ 01-03 ─▶ 01-04 ─▶ 02-01 ─▶ 03-01 ─▶ 03-02 ─▶ 03-05 ─▶ 04-02 ─▶ 04-06
             ├─▶ 00-04            └─▶ D-04 ─▶ D-05      ├─▶ 02-02 / 02-03 / 02-04 / D-06 / D-08 / 02-06
             ├─▶ 00-05                                  └─▶ 03-03 ─▶ 03-04
             └─▶ 00-06
```

| Phase | Est. (pd) |
|---|---|
| 0 — Scaffold | 2.5 |
| 1 — Chat core | 3.4 |
| 2 — Chat UX (silverpoint) | 3.4 |
| 3 — Embedding | 1.7 |
| 4 — Hardening & release | 2.5 |
| **Total** | **≈ 13.5** (10 bootstrap + 3.3 delta-10, minus merged overlap, + ≈0.9 silverpoint/uv) |

Parallelizable after Phase 0: `00-04`/`00-06` alongside Phase 1; `D-04`
alongside `01-03…01-05`; in Phase 2 everything after `02-01` fans out.

## 6. Risks specific to this plan

| Risk | Mitigation |
|---|---|
| Reflex 0.10 vs specs written for 0.8 (API drift in state/yield/lifespan) | `WCB-S-01` spike validates handlers, `rx.markdown`, lifespan hook for client close before Phase 1 |
| `prismal-sdk` not published → CI/Docker can't resolve a path source | Accepted: CI/Docker wait for the PyPI release (decision 2) |
| silverpoint has no chat component; hand-inked frames per bubble may be heavy on long transcripts | Stable `seed` per message; fall back to `mode="precision"` if render cost shows up in the a11y/perf pass |
| silverpoint palettes are monochrome; "accent color" may not map 1:1 | `S-02` maps accent to palette ink and validates contrast; documents the behaviour in `docs/configuration.md` |

## 7. Definition of Done (v0.1.0)

`TASKS.md` DoD, plus: `uv sync && uv run reflex run` from a fresh clone; the
panel is rendered with `reflex-silverpoint-react` components; AG-UI mode
works behind `PRISMAL_WEBCHAT_AGUI_ENABLED` with classic fallback; no usage
data reaches visitors by default; `budget_exceeded` shows the plain-language,
no-retry copy.

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-02 | Ernesto Crespo | Consolidated phases/tasks from bootstrap + DELTA-2026-10 + DELTA-2026-11 (uv, silverpoint) |
| 1.1 | 2026-11-02 | Ernesto Crespo | Delta accepted; SDK via PyPI (CI/Docker blocked until release); WCB-00-02 done |
