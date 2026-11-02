# DELTA 2026-11 — uv toolchain & silverpoint UI (prismal-webchat)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `ACCEPTED` (2026-11-02) |
| **Version** | 1.1 |
| **Date** | 2026-11-02 |
| **Applies to** | `webchat-bootstrap` (`ARCHITECTURE`/`SPEC`/`TASKS`) + `DELTA-2026-10-usage-agui` — folded into `0.1.0` |

## 1. Rationale

Stack decision: the chat UI is built with **`reflex-silverpoint-react`**
components, and the project is managed with **uv**. `reflex-silverpoint-react`
0.9.1 (latest on PyPI) requires `reflex>=0.10.0`, which contradicts the
original pin `reflex>=0.8,<0.9` (`SPEC-WCB-NFR-005`). Silverpoint ships no
dedicated chat component, so the panel is composed from its primitives
(`IMPLEMENTATION-PLAN.md` §3). `prismal-sdk` is not on PyPI; it is resolved
through a uv source. No boundary rule changes: silverpoint is a pure UI
dependency.

## 2. MODIFIED requirements

| ID | Change | EARS acceptance criterion |
|---|---|---|
| SPEC-WCB-NFR-005 | `reflex>=0.8,<0.9` → `reflex>=0.10,<0.11`; add `reflex-silverpoint-react>=0.9.1,<0.10`; Python floor `>=3.11` | THE SYSTEM SHALL declare these pins in `pyproject.toml` and commit `uv.lock`; a dependency test SHALL fail if they drift. |
| ARCHITECTURE §8 (Packaging) | "`uv`-based project" made concrete | THE SYSTEM SHALL be installable with `uv sync` and runnable with `uv run reflex run`; `prismal-sdk` SHALL be resolved via `[tool.uv.sources]` (path for local dev, git tag for CI/Docker). |

## 3. ADDED requirements

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-UI-001 | THE SYSTEM SHALL render the chat panel and input bar with `reflex-silverpoint-react` builders (`sp_surface`, `sp_avatar`, `sp_tag`, `sp_alert`, `sp_textarea`, `sp_button`, `sp_skeleton`, `sp_progress`) inside a `silverpoint_provider`; markdown stays with `rx.markdown`. | `MUST` |
| SPEC-WCB-UI-002 | THE SYSTEM SHALL derive `silverpoint_provider` ground/substrate/mode/palette only from non-secret settings (`theme`, `accent_color`) and SHALL validate the resulting palette's contrast at startup (`check_palette`), failing fast on an unreadable combination. | `SHOULD` |
| SPEC-WCB-UI-003 | Each message bubble SHALL carry a stable `id`/`seed` so its hand-inked frame does not change across re-renders. | `SHOULD` |

## 4. Tasks

| ID | Task | Est. | Dep | SPEC | Status |
|---|---|---|---|---|---|
| WCB-S-01 | Spike: reflex 0.10.x + silverpoint 0.9.1 under uv; state handlers, `rx.markdown`, lifespan hook verified | 0.3 d | — | NFR-005, UI-001 | `WIP` (boot + render verified; handlers/markdown/lifespan checked in WCB-01-*) |
| WCB-S-02 | Theme mapping settings → provider + contrast check (merged with WCB-02-05) | 0.2 d | S-01, 00-03 | UI-002 | `TODO` |
| WCB-S-03 | Panel/input built from silverpoint builders (merged with WCB-02-01) | 0.3 d | S-01, 01-04 | UI-001, UI-003 | `TODO` |

## 5. Out of scope

- Using silverpoint charts in the widget (no data viz in v0.1).
- Silverpoint styles in `embed.js` (the launcher runs on the host page; plain JS/CSS).

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-02 | Ernesto Crespo | Delta: uv toolchain, reflex 0.10 pin, silverpoint UI composition |
| 1.1 | 2026-11-02 | Ernesto Crespo | Accepted. Spike finding: Reflex backend moved to `:8001` (`:8000` is prismal-server's local default, `SPEC-WCB-APP-004`); SitemapPlugin disabled, RadixThemesPlugin explicit |
