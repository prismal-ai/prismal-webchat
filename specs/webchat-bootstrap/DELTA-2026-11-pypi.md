# DELTA 2026-11b — SDK from PyPI, host 0.3, CI/Docker/release (prismal-webchat)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `ACCEPTED` (2026-11-03) |
| **Version** | 1.0 |
| **Date** | 2026-11-03 |
| **Applies to** | `webchat-bootstrap` + `DELTA-2026-10-usage-agui` + `DELTA-2026-11-uv-silverpoint` — folded into `0.1.0` |
| **Unblocks** | WCB-00-06 (CI), WCB-04-03 (Docker + deploy doc), WCB-04-06 (release) |

## 1. Rationale

The upstream packages were released on 2026-11-02/03:

| Package | PyPI | Note |
|---|---|---|
| `prismal-sdk` | **`prismal-ai-sdk` 0.3.0** | PyPI refused `prismal-sdk` (too close to `prismai-sdk`); the import module is still `prismal_sdk`. 0.3 adds `run_agui` (AG-UI resume) on top of the 0.2 surface the webchat already uses. |
| `prismal-server` | `prismal-server` 0.3.0 | Targets `prismal-ai` 3.22.1; fake-LLM mode unchanged. |
| `prismal` (engine) | `prismal-ai` 3.22.1 | Never a webchat dependency. |
| `prismal-tui` | `prismal-tui` 0.2.0 | Sibling client; same SDK pin (`prismal-ai-sdk>=0.3,<1`). |

The sibling-checkout uv source (DELTA-2026-11 §2, ARCHITECTURE §8) no longer
resolves — the checkout's distribution is now named `prismal-ai-sdk` — and
was always meant to be temporary. Every SDK symbol the webchat imports is
unchanged in 0.3.0 (unit suite, contract 7/7 against host 0.3.0, compile 4/4);
the only code change is the `ForbiddenError` row below.

## 2. MODIFIED requirements

| ID | Change | EARS acceptance criterion |
|---|---|---|
| SPEC-WCB-NFR-005 | `prismal-sdk>=0.2.0.dev0,<1` → **`prismal-ai-sdk>=0.3,<1`** | THE SYSTEM SHALL depend on the PyPI distribution `prismal-ai-sdk` and SHALL NOT resolve it from a path source; the dependency test SHALL also forbid `prismal-ai` (engine), `prismal-server`, `prismal-sdk` (old name) and `httpx` as runtime dependencies. |
| ARCHITECTURE §8 (Packaging) | `[tool.uv.sources]` entry removed | THE SYSTEM SHALL be installable with `uv sync --locked` from a clean clone with no sibling repositories. |
| SPEC-WCB-ERR-001 / ARCHITECTURE §6 | `ForbiddenError` joins the "can't be processed" row | SDK 0.3 raises `ForbiddenError` for the host's `403 forbidden` / `forbidden_tenant` on every route (it used to be the base `PrismalAPIError` → generic text). WHEN a turn fails with `ForbiddenError` THE SYSTEM SHALL render "That request can't be processed." with Retry, and no code. |
| ARCHITECTURE §8 (Packaging) | "A deployable app, no wheel build" → **also a PyPI distribution** (owner decision 2026-11-03) | THE SYSTEM SHALL build a wheel and sdist named `prismal-webchat` (hatchling) that contain the `prismal_webchat` package plus the Reflex working-directory files under `prismal_webchat/_app/`. |
| SPEC-WCB-NFR-002 (CI) | Contract job installs `prismal-server>=0.3,<0.4` from PyPI in its own venv and starts it in fake-LLM mode | WHEN a pull request is opened THE CI SHALL run unit, contract (against the fake-LLM host), compile and Docker smoke jobs; the contract job SHALL fail, not skip, when the host does not come up. |

## 3. ADDED requirements

| ID | Requirement | Prio |
|---|---|---|
| SPEC-WCB-DEP-001 | THE SYSTEM SHALL ship a container image that runs a single `reflex run --env prod --single-port` process as a non-root user, builds the frontend at startup from the runtime environment (branding is compile-time), and needs no network access at startup. | `MUST` |
| SPEC-WCB-DEP-002 | WHEN the image runs THE SYSTEM SHALL serve `/chat/` with the `frame-ancestors` CSP, `/embed.js`, and `/ping`, and SHALL NOT serve the bearer token in either asset (`scripts/docker_smoke.sh`). | `MUST` |
| SPEC-WCB-REL-001 | WHEN a final version that is not on PyPI reaches `main` THE release workflow SHALL run the gates and the artifact smoke tests, upload the wheel and sdist to PyPI with trusted publishing (environment `pypi`, `main` only, no stored token), push `ghcr.io/<repo>:<version>` and `:latest`, then tag `v<version>` and create the GitHub release from the `CHANGELOG.md` section with the artifacts attached. | `MUST` |
| SPEC-WCB-REL-002 | THE distribution SHALL install a `prismal-webchat` console script: `init [DIR]` writes `rxconfig.py`, `assets/embed.js` and `reflex.lock/` from the installed package; `run` does the same and execs `reflex run` there (prod single-port by default). Settings SHALL stay in the environment, never on the command line. `scripts/smoke_test.py` SHALL verify an installed wheel compiles the app from an empty directory. | `MUST` |

## 4. Not adopted (recorded)

| Item | Decision |
|---|---|
| WebSocket transport to the host (`client.ws()`, host 0.2+) — `WCB-FUTURE-01` trigger met | **Deferred past 0.1.0.** SSE through `send_message` already streams and cancels correctly; WS would add the optional `[ws]` extra and a second transport path for no visitor-visible gain in v0.1. Revisit with a delta spec when there is a need (e.g. server-pushed events). |
| AG-UI interrupt resume (`run_agui(resume=…)`, SDK 0.3) | **Out of scope for 0.1.0.** The webchat has no human-in-the-loop UI; an interrupted run ends the turn normally. Needs its own delta (UI for approving/answering interrupts). |
