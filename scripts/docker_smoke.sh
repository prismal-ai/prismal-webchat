#!/usr/bin/env bash
# WCB-04-03 — boot the image and check what only a prod single-port build has:
# the page, embed.js, the frame-ancestors CSP, and no token in what it serves.
#
#   scripts/docker_smoke.sh <image> [host-port]
set -euo pipefail

IMAGE="${1:?usage: docker_smoke.sh <image> [host-port]}"
PORT="${2:-18001}"
TOKEN="wcb-smoke-token-SENTINEL-2d9e"
ORIGIN="https://smoke.example.com"
NAME="prismal-webchat-smoke-$$"
BASE="http://127.0.0.1:${PORT}"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8001" \
  -e PRISMAL_WEBCHAT_TOKEN="$TOKEN" \
  -e PRISMAL_WEBCHAT_EMBED_ORIGINS="[\"${ORIGIN}\"]" \
  -e PRISMAL_WEBCHAT_TITLE="Smoke Assistant" \
  "$IMAGE" >/dev/null

echo "waiting for ${BASE}/ping …"
for _ in $(seq 1 180); do
  if curl -fsS "${BASE}/ping" >/dev/null 2>&1 && curl -fsS -o /dev/null "${BASE}/chat/" 2>/dev/null; then
    break
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != "true" ]; then
    echo "container exited"; docker logs "$NAME"; exit 1
  fi
  sleep 2
done

fail() { echo "FAIL: $*"; docker logs "$NAME" | tail -50; exit 1; }

headers="$(curl -fsS -D - -o /dev/null "${BASE}/chat/")" || fail "/chat/ did not answer 200"
echo "$headers" | grep -i '^content-security-policy:' | grep -q "frame-ancestors 'self' ${ORIGIN}" \
  || fail "frame-ancestors CSP missing or wrong: $(echo "$headers" | grep -i content-security)"

page="$(curl -fsS "${BASE}/chat/")"
loader="$(curl -fsS "${BASE}/embed.js")" || fail "/embed.js did not answer 200"
echo "$loader" | grep -q "PrismalChat" || fail "/embed.js is not the loader"

for body in "$page" "$loader"; do
  if grep -q "$TOKEN" <<<"$body"; then fail "token leaked into a served asset"; fi
done

echo "OK: page, embed.js and CSP served; token absent"
