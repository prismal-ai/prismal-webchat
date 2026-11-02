# Configuration

All settings are environment variables with the `PRISMAL_WEBCHAT_` prefix,
read once at startup by `WebchatSettings` (`prismal_webchat/settings.py`).
Invalid values stop the process at boot — there is no "warn and continue".

The settings object is **backend-only**. Only presentation values (title,
welcome text, colours) reach the page; the token, org id and server URL never
do (verified by `tests/unit/test_secret_hygiene.py` and, against a real
build, `uv run pytest -m compile`).

| Env var | Default | Validation / meaning |
|---|---|---|
| `PRISMAL_WEBCHAT_SERVER_URL` | `http://localhost:8000` | Absolute `http(s)://` URL of `prismal-server`; trailing `/` dropped. |
| `PRISMAL_WEBCHAT_TOKEN` | — | Service bearer credential. Passed only to the `prismal-sdk` client constructor; never in state, logs or assets. |
| `PRISMAL_WEBCHAT_ORG_ID` | — | Tenant applied to every request by the SDK (`X-Org-Id`). |
| `PRISMAL_WEBCHAT_TITLE` | `prismal` | Page/widget title. |
| `PRISMAL_WEBCHAT_WELCOME_MESSAGE` | `Hi! How can I help?` | First assistant bubble. Presentational: never sent to the engine. Markdown. |
| `PRISMAL_WEBCHAT_ACCENT_COLOR` | `#5D4BE5` | `#RRGGBB`. Becomes the silverpoint **ink** on the light look and must pass silverpoint's contrast check (4.5:1 on the cream ground) or startup fails with the failing pairs listed. Not applied on the dark look. |
| `PRISMAL_WEBCHAT_THEME` | `light` | `light` (silverpoint ground, cream), `dark` (cyanotype ground: white line on Prussian blue), `auto` (follows the visitor's `prefers-color-scheme`). |
| `PRISMAL_WEBCHAT_EMBED_ORIGINS` | `[]` | JSON list of origins allowed to iframe the chat, each exactly `scheme://host[:port]` (no path, no wildcard). Empty ⇒ same origin only. See [embedding](./embedding.md). |
| `PRISMAL_WEBCHAT_AGUI_ENABLED` | `false` | Stream turns with AG-UI events (tool chips per call, sub-agent progress line). Falls back to the classic stream, for the rest of the process, if the server answers `protocol_not_enabled`. See [agui](./agui.md). |
| `PRISMAL_WEBCHAT_SHOW_USAGE` | `false` | Show a muted "N tokens" footer under each reply. Never cost, model or gateway. Off ⇒ no usage data enters page state at all. |

## Choosing an accent

The default `#6C5CE7` from the original spec measures 3.94:1 on the cream
ground, below silverpoint's 4.5:1, so the shipped default is the same hue,
darker: `#5D4BE5` (4.73:1). To check a candidate before deploying:

```bash
uv run python -c "from reflex_silverpoint_react import contrast_ratio as c; print(c('#0EA5E9', '#EDE7DA'))"
```

## Ports

| Mode | Frontend | Backend |
|---|---|---|
| `uv run reflex run` (dev) | `:3000` (Vite) | `:8001` |
| `uv run reflex run --env prod --single-port --frontend-port 8001 --backend-port 8001` | `:8001` | `:8001` |

The backend avoids `:8000`, `prismal-server`'s local default.
