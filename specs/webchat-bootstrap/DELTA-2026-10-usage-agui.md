# DELTA 2026-10 — usage & AG-UI (prismal-webchat)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `READY` |
| **Version** | 1.0 |
| **Date** | 2026-10-04 |
| **Applies to** | `webchat-bootstrap` (`PLAN`/`ARCHITECTURE`/`SPEC`/`TASKS`) — folded into `0.1.0` |
| **Source** | `prismal/docs/gap-analysis-gateways-tokens-decisions-2026-10.md` §6 |

## 1. Rationale

`prismal-server` 0.2 adds usage to the `done` event, budget enforcement
surfaced as a `budget_exceeded` error, and an **AG-UI 1.0** stream mode with
richer tool-call and sub-agent lifecycle events. The webchat is a
visitor-facing widget: it should (a) optionally render richer agent progress
through AG-UI, (b) **never show cost or token data to visitors by default**,
and (c) explain a budget refusal in plain language instead of a generic error.
No engine logic moves into the widget.

## 2. Dependencies

- `prismal-sdk` `>=0.2,<1` (`SPEC-CS2-*`): `Usage`, `DoneEvent.usage`, `send_message(..., protocol="ag-ui")`
  yielding `AgUiEvent` subclasses (`RunStarted`, `RunFinished`, `TextMessageStart/Content/End`,
  `ToolCallStart/Args/End/Result`, `StateSnapshot`, `StateDelta`, `SubagentStarted/Finished`,
  `Interrupt`, `CustomEvent`, `PrismalUsageEvent`); `RunError` is **raised** as the mapped
  `PrismalAPIError` subclass (`SPEC-CS2-AGU-003`); `ProtocolNotEnabledError` on `406`.
- `prismal-server` `0.2.0` (RH2) with AG-UI mode (`host_agui_enabled` + engine `agui_events_enabled`);
  contract tests use `host_fake_llm_mode`.
- The widget dispatches on the SDK classes only, so AG-UI wire-name changes stay inside the SDK.
  Resolved: `budget_exceeded` (HTTP 402 before the turn, terminal `error` event mid-stream) is defined in
  RH2 §11 and mapped to `BudgetExceededError` in CS2 §7 (`WCB-D-01` only pins the fixture).

## 3. MODIFIED requirements

| ID | Change | EARS acceptance criterion |
|---|---|---|
| SPEC-WCB-NFR-005 | SDK pin `prismal-sdk>=0.1,<1` → `>=0.2,<1` | THE SYSTEM SHALL declare `prismal-sdk>=0.2,<1` in `pyproject.toml`; a dependency test SHALL fail on a lower floor. |
| SPEC-WCB-CHT-003 | Streaming loop accepts either the classic SSE events or AG-UI events, chosen by settings | WHERE `agui_enabled` is `False`, THE SYSTEM SHALL call `send_message(...)` without `protocol` and render exactly as in 0.1 (snapshot test). |
| SPEC-WCB-ERR-002 | Error table gains `budget_exceeded` and `ProtocolNotEnabledError` | WHEN a turn fails with a `PrismalAPIError` whose `code == "budget_exceeded"`, THE SYSTEM SHALL render "This assistant has reached its usage limit for now. Please try again later." with no retry button, no amount, and no code. |

## 4. ADDED requirements

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-CFG-004 | THE SYSTEM SHALL add settings `PRISMAL_WEBCHAT_AGUI_ENABLED: bool = False` and `PRISMAL_WEBCHAT_SHOW_USAGE: bool = False`, both non-secret. | `MUST` |
| SPEC-WCB-AGU-001 | WHERE `agui_enabled` is `True`, WHEN a visitor sends a message, THE SYSTEM SHALL call `send_message(thread_id, content, protocol="ag-ui")` and consume the yielded `AgUiEvent` objects. | `MUST` |
| SPEC-WCB-AGU-008 | IF `send_message(..., protocol="ag-ui")` raises `ProtocolNotEnabledError`, THEN THE SYSTEM SHALL resend the same content once with the default `protocol="prismal"`, render it classically, and use the classic protocol for the rest of the process (logged once). | `MUST` |
| SPEC-WCB-AGU-002 | WHILE AG-UI mode is active, WHEN a `TextMessageContent` arrives, THE SYSTEM SHALL append its `delta` to the assistant bubble exactly as a `TokenEvent` would. | `MUST` |
| SPEC-WCB-AGU-003 | WHEN a `ToolCallStart` arrives, THE SYSTEM SHALL show a tool chip labelled with `tool_call_name` in a "running" state keyed by `tool_call_id`; WHEN the matching `ToolCallEnd` or `ToolCallResult` (same `tool_call_id`) arrives, THE SYSTEM SHALL mark it "done". `ToolCallArgs.delta` and `ToolCallResult.content` SHALL NOT be rendered to visitors. | `MUST` |
| SPEC-WCB-AGU-004 | WHEN `SubagentStarted` arrives, THE SYSTEM SHALL show a single "working on: <name>" progress line (fallback "working…" when `name` is `None`); WHEN `SubagentFinished` with the same `subagent_id` arrives, THE SYSTEM SHALL clear it (at most one line visible). | `SHOULD` |
| SPEC-WCB-AGU-005 | IF the SDK yields a base `AgUiEvent` (unknown `type`), a non-usage `CustomEvent`, an `Interrupt`, `RunStarted`, `TextMessageStart`/`TextMessageEnd` or `ToolCallArgs`, THEN THE SYSTEM SHALL change no visible state beyond the rules above, log `type` only at debug level, and continue. | `MUST` |
| SPEC-WCB-AGU-006 | WHEN `RunFinished` arrives (iteration ends), THE SYSTEM SHALL close the turn exactly as `DoneEvent` does in classic mode; WHEN the iterator raises the exception mapped from `RunError`, THE SYSTEM SHALL apply the same error mapping and keep partial text. | `MUST` |
| SPEC-WCB-AGU-007 | THE SYSTEM SHALL ignore `StateSnapshot`/`StateDelta` events in the visitor UI (no state is rendered). | `MUST` |
| SPEC-WCB-USG-001 | WHERE `show_usage` is `False` (default), THE SYSTEM SHALL render no token, cache, cost, model or gateway information anywhere in the widget, and SHALL NOT place `Usage` values in `rx.State`. | `MUST` |
| SPEC-WCB-USG-002 | WHERE `show_usage` is `True`, WHEN a turn completes with a `Usage` (from `DoneEvent.usage` or `PrismalUsageEvent.usage`), THE SYSTEM SHALL render a muted footer "`total_tokens` tokens" under the reply — never `cost_usd`, `served_model` or `gateway`. | `MAY` |
| SPEC-WCB-USG-003 | IF `DoneEvent.usage` is `None` or no `PrismalUsageEvent` arrives before `RunFinished`, THEN THE SYSTEM SHALL complete the turn normally (fail-open). | `MUST` |

## 5. Tasks (appended to `TASKS.md`)

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-D-01 | **Verify before build**: pin the `budget_exceeded` fixture from RH2 §11 / CS2 §7; write `docs/agui.md` mapping table (CS2 class → widget effect) | 0.2 d | — | ERR-002, AGU-* | `TODO` |
| WCB-D-02 | Bump SDK pin to `>=0.2,<1`; extend `FakeAsyncPrismalClient` with `protocol="ag-ui"` scripts (CS2 event classes, `RunError` raise, `ProtocolNotEnabledError`) and `DoneEvent.usage` | 0.4 d | D-01 | NFR-005 | `TODO` |
| WCB-D-03 | Settings `agui_enabled`, `show_usage` + validation tests | 0.2 d | D-02 | CFG-004 | `TODO` |
| WCB-D-04 | `state/agui_mapper.py`: pure `AgUiEvent` → chat-state mutation by `isinstance` on CS2 classes (text, tool chip by `tool_call_id`, sub-agent line by `subagent_id`, run end, ignore state/unknown) | 0.7 d | D-02 | AGU-002..007 | `TODO` |
| WCB-D-05 | Wire mapper into `ChatState.send()` behind `agui_enabled`; `ProtocolNotEnabledError` fallback; flag-off snapshot test | 0.4 d | D-03, D-04 | AGU-001, AGU-008, CHT-003 | `TODO` |
| WCB-D-06 | Sub-agent progress line + tool chip states in `components/chat_panel` (a11y live region) | 0.4 d | D-04 | AGU-003, -004 | `TODO` |
| WCB-D-07 | `budget_exceeded` row in error table (by `PrismalAPIError.code`); no-retry bubble | 0.2 d | D-02 | ERR-002 | `TODO` |
| WCB-D-08 | Visitor usage policy: state/asset scan proves no usage fields when `show_usage=False`; optional token footer | 0.4 d | D-03 | USG-001..003 | `TODO` |
| WCB-D-09 | Contract test vs `prismal-server` 0.2 `host_fake_llm_mode`: classic turn, AG-UI turn (`/tool` → chip, `PrismalUsageEvent`), `/error` → error bubble (budget refusal stays fake-client only) | 0.4 d | D-05, D-07 | AGU-001, AGU-003, AGU-006 | `TODO` |

Delta estimate: **~3.3 person-days**.

## 6. Test notes

- Mapper tests are table-driven: one scripted AG-UI sequence per case
  (text-only, `ToolCallStart`/`ToolCallEnd`, nested `SubagentStarted`, unknown base `AgUiEvent`, raised `RunError` mapping, `ProtocolNotEnabledError` fallback).
- Interleaving test: tool chip opened mid-text keeps text order intact.
- Privacy test (`USG-001`): serialize every `rx.State` subclass after a turn
  with usage and assert no `cost_usd`, `cost_source`, `served_model`,
  `gateway`, `*_tokens` keys or values; scan compiled `.web/` output likewise.
- Flag-off snapshot: identical rendered transcript to 0.1 for the classic script.

## 7. Out of scope

- Showing cost, model, gateway or budget figures to visitors.
- AG-UI human-in-the-loop interrupts (approve/deny in the widget).
- Rendering tool arguments/results or agent state to visitors.
- Usage history or per-visitor budgets (`WCB-FUTURE-03` remains).
- WebSocket transport (`WCB-FUTURE-01` remains; server WS exists in RH2 but the widget keeps SSE in 0.1).

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-04 | Ernesto Crespo | Delta: AG-UI rendering, visitor usage policy, budget copy |
