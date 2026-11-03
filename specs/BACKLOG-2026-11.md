# BACKLOG — 2026-11

| Field | Value |
|---|---|
| **Status** | `OPEN` |
| **Date** | 2026-11-03 |
| **Source** | Cross-repo review of `prismal-ai` (specs, TASKS, git history, tags, PyPI) — see `prismal-ai-arquitectura.excalidraw`, section 7 |
| **Repo** | `prismal-webchat` |

Open items found on 2026-11-03 that are not yet done. Each row points to the spec or
TASKS row that owns it; this file does not replace those, it tracks what is still open.
Priorities: **P1** blocks a release or the current wave · **P2** next feature work ·
**P3** hygiene or future horizon. Status legend: `TODO` · `WIP` · `DONE` · `BLOCKED`.

| ID | P | Item | Source | Done when | Status |
|---|---|---|---|---|---|
| BL-01 | P1 | **Merge the implementation.** WCB phases 0–4 + DELTA-2026-10 + DELTA-2026-11 live on `feat/wcb-00-scaffold-uv`; `main` only has the SDD seed. | `git log` | PR merged to `main` | `TODO` — PR #1 updated 2026-11-03 with the release work; merge awaits owner approval |
| BL-02 | P1 | **Update TASKS.md.** Only WCB-00-01 is `DONE`; the commits cite WCB-00-02..05, WCB-01-*, WCB-02-*, WCB-03-*, WCB-04-01/02/04/05, D-01..D-09 and S-01..03. Mark each row against the code and leave open the three rows with no code yet: WCB-00-06 (CI workflow), WCB-04-03 (Dockerfile + `docs/deploy.md`), WCB-04-06 (tag + release workflow). | `specs/webchat-bootstrap/TASKS.md` | Every row reflects the code | `DONE` (2026-11-03: 26/29 DONE with commit refs) |
| BL-03 | P1 | **Release v0.1.0.** Version is still `0.1.0.dev0`; no tag, no CHANGELOG. | `pyproject.toml` | `v0.1.0` tagged with CHANGELOG | `WIP` — version `0.1.0`, `CHANGELOG.md`, `release.yml` ready; tag + GHCR image are created by `release.yml` when BL-01 merges |
| BL-04 | P2 | **WCB-FUTURE-01 WebSocket transport — trigger met.** `prismal-server` ships WS (v0.2.0) and `prismal-sdk` has `client.ws()`. | `specs/webchat-bootstrap/TASKS.md` Future | Decision to schedule; delta spec if yes | `DONE` (2026-11-03: deferred past 0.1.0, recorded in `DELTA-2026-11-pypi.md` §4 and TASKS WCB-FUTURE-01) |
| BL-05 | P3 | **Untracked build leftovers.** `__pycache__/` at the repo root; confirm it is ignored. | `ls` | Covered by `.gitignore` | `DONE` (`__pycache__/` is ignored; nothing tracked) |

## Cross-repo dependencies

- Uses `prismal-sdk` AG-UI mapping; AG-UI resume (sdk 0.3 `run_agui`) is not used yet —
  tracked as `WCB-FUTURE-07`; an interrupted run ends the turn (test pinned).
- 2026-11-03: SDK now resolves from PyPI as `prismal-ai-sdk>=0.3,<1`; CI contract job
  runs against `prismal-server>=0.3,<0.4` from PyPI (`DELTA-2026-11-pypi.md`).
