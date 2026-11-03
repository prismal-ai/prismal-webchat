# Deploy

The webchat is **one process on one port**. In production it runs as

```bash
reflex run --env prod --single-port --frontend-port 8001 --backend-port 8001 --backend-host 0.0.0.0
```

and that process serves everything the browser needs: the compiled page
(`/` and the bare `/chat` route), the loader (`/embed.js`), and the Reflex
WebSocket (`/_event`) that carries every chat turn. It is also the only
place the `frame-ancestors` CSP header exists: `reflex run` in dev mode
serves the page from Vite on `:3000` without it (see
[`embedding.md`](./embedding.md)).

The browser never talks to `prismal-server`. The webchat backend does,
through `prismal-sdk`, with the service token from its own environment.

## From PyPI

```bash
pip install prismal-webchat
prismal-webchat run --app-dir /srv/webchat --port 8001
```

`run` writes `rxconfig.py`, `assets/embed.js` and the pinned `reflex.lock/`
into the app directory (refreshing them on every start, so they always
match the installed version), then execs the command above. The first start
needs network access for bun and the frontend packages; later starts reuse
them from the app directory. Settings come from the environment exactly as
in the container. Run it under a process supervisor (systemd, supervisord)
with one instance.

## Container image

```bash
docker build -t prismal-webchat .
docker run --rm -p 8001:8001 \
  -e PRISMAL_WEBCHAT_SERVER_URL=https://prismal-server.internal:8000 \
  -e PRISMAL_WEBCHAT_TOKEN="$PRISMAL_TOKEN" \
  -e PRISMAL_WEBCHAT_EMBED_ORIGINS='["https://www.example.com"]' \
  -e PRISMAL_WEBCHAT_TITLE="Acme Assistant" \
  prismal-webchat
```

- **Port**: `8001` by default; set `PORT` to change it inside the container.
- **Health**: `GET /ping` (Reflex's liveness route) — used by the image's
  `HEALTHCHECK`.
- **Startup builds the frontend.** Title, welcome text, accent colour and
  theme are compiled into the page, so the container compiles the frontend
  from its own environment when it starts (about 10–30 s; the healthcheck's
  start period is 120 s). The image already contains bun and `node_modules`,
  so startup needs no network access. Changing a branding variable means
  restarting the container, not rebuilding the image.
- **User**: runs as the non-root user `app` (uid 10001).
- **Secrets**: pass `PRISMAL_WEBCHAT_TOKEN` from your secret store. It is
  read by the backend only; `scripts/docker_smoke.sh` checks that the served
  page and `embed.js` do not contain it.

Every setting is listed in [`configuration.md`](./configuration.md).

### Smoke test

```bash
scripts/docker_smoke.sh prismal-webchat        # boots it, checks page, embed.js, CSP, no token
```

CI runs the same script on every pull request.

## Reverse proxy

Put TLS in front of the container and forward **both** plain HTTP and the
WebSocket upgrade to the same upstream. Without the upgrade headers the page
loads but no message is ever sent.

nginx:

```nginx
location / {
    proxy_pass         http://webchat:8001;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_set_header   Host $host;
    proxy_set_header   X-Forwarded-Proto $scheme;
    # A turn can stream for a while; don't cut the socket mid-answer.
    proxy_read_timeout 300s;
}
```

Caddy upgrades WebSockets automatically:

```
chat.example.com {
    reverse_proxy webchat:8001
}
```

Do **not** add or override `Content-Security-Policy` / `X-Frame-Options` at
the proxy: the backend's `frame-ancestors` header is the embedding policy,
and a proxy-level `X-Frame-Options: DENY` would block every embed.

## Single process, single replica

Reflex keeps each tab's state (thread id, messages, in-flight turn) in the
memory of the process that owns its WebSocket. For v0.1:

- run **one replica** with **one worker**;
- a restart drops the open tabs' UI state — the conversation itself is
  safe in the engine's checkpointer under the tab's `thread_id`, but a
  reloaded tab starts a new thread (multi-conversation UI is
  `WCB-FUTURE-02`);
- scaling out needs an external Reflex state manager (Redis) and sticky
  WebSocket routing — tracked as `WCB-FUTURE-06`, not supported yet.

## Upstream

`PRISMAL_WEBCHAT_SERVER_URL` must be reachable **from the container**, not
from the visitor's browser. `localhost` inside the container is the
container itself: use the service name on a shared Docker network, or
`--add-host host.docker.internal:host-gateway` and a host bound to an
address the container can reach when the server runs on the Docker host.

The webchat targets `prismal-server` 0.3.x (contract suite in CI) through
`prismal-ai-sdk>=0.3,<1`.
