# Embedding

## One tag

```html
<script src="https://chat.example.com/embed.js" async></script>
```

`embed.js` adds a launcher button (bottom-right). The first click creates an
iframe of the webchat's bare `/chat` route; further clicks, `Escape`, or the
chat's own **Close** button hide it.

The loader learns the webchat origin from its own `<script src>`; it contains
no server URL, tenant or credential, and needs no configuration.

## Allow the host site

Embedding is **off by default**. List every site that may frame the chat:

```bash
export PRISMAL_WEBCHAT_EMBED_ORIGINS='["https://www.example.com", "https://shop.example.com"]'
```

Every response from the webchat backend carries

```
Content-Security-Policy: frame-ancestors 'self' https://www.example.com https://shop.example.com
```

so the **browser** refuses to render the chat inside any other site. Origins
are exact (`scheme://host[:port]`); `www.example.com` and `example.com` are
different origins. Wildcards are rejected at startup.

> The header is added by the Python backend (an ASGI middleware installed as
> Reflex's `api_transformer`). In `reflex run` dev mode the page is served by
> Vite on `:3000` and does **not** carry it — verify the allowlist in prod
> mode (`--env prod --single-port`) or in the container. `frame-ancestors`
> cannot be set from a `<meta>` tag.

## Page API

```js
window.PrismalChat.open();
window.PrismalChat.close();
window.PrismalChat.toggle();
```

The chat itself can ask the loader to open or close the widget with
`postMessage({type: "prismal-chat:open" | "prismal-chat:close"})`. The loader
acts only on messages whose `event.origin` is the webchat origin; anything
else (including the host page messaging itself) is ignored.

## Try it locally

```bash
# terminal 1 — a prismal-server (fake LLM, no credentials)
PRISMAL_SERVER_HOST_FAKE_LLM_MODE=true uvicorn prismal_server.app:app   # in prismal-server

# terminal 2 — the webchat in prod mode, allowing the demo origin
PRISMAL_WEBCHAT_EMBED_ORIGINS='["http://localhost:5500"]' \
  uv run reflex run --env prod --single-port --frontend-port 8001 --backend-port 8001

# terminal 3 — a "third-party" page
uv run python -m http.server 5500 --bind 0.0.0.0 --directory prismal_webchat/embed
```

- <http://localhost:5500/demo.html?chat=http://localhost:8001> — allowed: the
  chat opens and works.
- <http://127.0.0.1:5500/demo.html?chat=http://localhost:8001> — a different
  origin: the iframe is refused (the console shows the CSP violation).

The checklist is also at the top of `prismal_webchat/embed/demo.html`.
