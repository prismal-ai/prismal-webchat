# AG-UI mode

`PRISMAL_WEBCHAT_AGUI_ENABLED=true` asks `prismal-server` (≥ 0.2) for AG-UI
1.0 events (`send_message(..., protocol="ag-ui")`) instead of the classic
`token` / `tool_call` / `done` stream. The server needs AG-UI on
(`host_agui_enabled`, default true) and the engine needs
`PRISMAL_AGUI_EVENTS_ENABLED=true`.

If the server answers `406 protocol_not_enabled` (`ProtocolNotEnabledError`,
raised before any event), the webchat resends the **same content once** with
the classic protocol and stays classic for the rest of the process (logged
once).

## Event → widget effect

The widget dispatches on `prismal_sdk.agui` classes only
(`prismal_webchat/state/agui_mapper.py`), so AG-UI wire-name changes stay in
the SDK.

| SDK class | Effect | SPEC |
|---|---|---|
| `TextMessageContent` | append `delta` to the live assistant bubble | AGU-002 |
| `ToolCallStart` | add a chip "using `tool_call_name`…", keyed by `tool_call_id` | AGU-003 |
| `ToolCallEnd`, `ToolCallResult` (same id) | mark that chip done (✓) | AGU-003 |
| `ToolCallArgs`, `ToolCallResult.content` | **never rendered** | AGU-003 |
| `SubagentStarted` | one line "working on: `name`" (fallback "working…") | AGU-004 |
| `SubagentFinished` (same `subagent_run_id`) | clear that line; a finish for another run is ignored | AGU-004 |
| `PrismalUsageEvent` | `total_tokens` footer **only** with `SHOW_USAGE=true`; otherwise nothing enters state | USG-001/002 |
| `RunFinished` | close the turn (chips and progress line cleared) | AGU-006 |
| exception raised from `RUN_ERROR` | same error mapping as classic; partial text kept | AGU-006 |
| `StateSnapshot`, `StateDelta` | ignored | AGU-007 |
| `RunStarted`, `TextMessageStart/End`, `StepStarted/Finished`, non-usage `CustomEvent`, unknown base `AgUiEvent` | no visible change; `type` logged at debug | AGU-005 |

## Notes from WCB-D-01

- DELTA-2026-10 calls the sub-agent key `subagent_id`; the SDK field is
  **`subagent_run_id`**, which the widget uses.
- `budget_exceeded` is mapped by `PrismalAPIError.code`, so the host's `402`
  before a turn, a v0.1 host's `429`, and a terminal stream error mid-turn all
  render "This assistant has reached its usage limit for now. Please try again
  later." with no retry and no figures. Fixture:
  `tests/scripts.py::budget_exceeded` (402, `scope`/`limit`/`consumed`).
