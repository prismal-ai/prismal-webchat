# prismal-webchat — single-port production image (WCB-04-03).
#
# One process, one port: `reflex run --env prod --single-port` serves the
# compiled frontend, the Reflex WebSocket (/_event) and embed.js from the
# Python backend, which is also the only place the frame-ancestors CSP header
# exists (docs/embedding.md). See docs/deploy.md.
#
# Branding settings (title, welcome text, accent, theme) are compiled into the
# frontend, so the frontend is built when the container starts, from the
# runtime environment. The image build warms everything that needs the network
# (bun, node_modules) so startup only runs the offline Vite build.
#
# Build:  docker build -t prismal-webchat .
# Run:    docker run -p 8001:8001 -e PRISMAL_WEBCHAT_SERVER_URL=… prismal-webchat
FROM python:3.13-slim

# unzip: Reflex's bun installer. curl: bun download + HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    REFLEX_TELEMETRY_ENABLED=false \
    PORT=8001

WORKDIR /app
RUN chown app:app /app
USER app

# Dependencies first (cached on lockfile-only changes); runtime deps only.
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=app:app rxconfig.py README.md LICENSE ./
COPY --chown=app:app assets ./assets
COPY --chown=app:app prismal_webchat ./prismal_webchat

# Warm-up build with placeholder settings: installs bun and node_modules into
# the image. The real build runs at startup with the deployment's settings.
RUN reflex export --frontend-only --no-zip --env prod --loglevel warning \
    && rm -rf .web/build

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/ping" || exit 1

# Single process, single worker: Reflex state lives in this process
# (WCB-FUTURE-06 covers multi-worker deploys).
CMD ["sh", "-c", "exec reflex run --env prod --single-port --frontend-port \"$PORT\" --backend-port \"$PORT\" --backend-host 0.0.0.0"]
