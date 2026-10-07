#!/bin/sh
# End-to-end page tests with Playwright, on the fake transcriber or on the real model.
#   scripts/e2e.sh fake   Docker only, no GPU: the app runs with YT_FAKE=1.
#   scripts/e2e.sh real   Docker and GPU: compose runs the real model, video KnXm3PbNz5A.
# The Playwright container shares the host network to reach localhost:8000.
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=${1:-}
# Same version as e2e/requirements.txt: the image ships the browsers of that version.
PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright/python:v1.63.0-noble
APP_IMAGE=yt-transcriber-e2e
APP_NAME=yt-transcriber-e2e-app
PW_NAME=yt-transcriber-e2e-pw
# Set once the guards have passed: cleanup only touches what this run started.
STARTED=

wait_for_page() {
  i=0
  until curl -sf -o /dev/null http://localhost:8000/; do
    i=$((i + 1))
    [ "$i" -gt "${1:-60}" ] && { echo "the page does not answer on :8000" >&2; return 1; }
    sleep 2
  done
}

ensure_port_free() {
  # uvicorn loads the model before opening the port: a compose stack still loading does not answer yet.
  if [ -n "$(docker compose -f "$ROOT/compose.yaml" ps -q 2>/dev/null)" ] ||
    [ -n "$(docker ps -aq --filter "name=^$APP_NAME$")" ]; then
    echo "an app stack is already running: run docker compose down, or docker rm -f $APP_NAME, before the e2e" >&2
    exit 1
  fi
  rc=0
  curl -s -o /dev/null --max-time 2 http://localhost:8000/ || rc=$?
  if [ "$rc" -eq 127 ]; then
    echo "curl not found: install it on the host, it probes port 8000" >&2
    exit 1
  fi
  # 7 = connection refused, the port is free. Any other code: something is listening.
  if [ "$rc" -ne 7 ]; then
    echo "port 8000 is already in use (curl rc=$rc): stop whatever listens before the e2e" >&2
    exit 1
  fi
}

cleanup() {
  status=$?
  # A run refused by the guards started nothing: it must not stop anything.
  [ -n "$STARTED" ] || return 0
  if [ "$status" -ne 0 ]; then
    echo "--- app logs (statut $status) ---" >&2
    if [ "$STARTED" = real ]; then
      docker compose -f "$ROOT/compose.yaml" logs --tail 40 >&2 2>&1 || true
    else
      docker logs --tail 40 "$APP_NAME" >&2 2>&1 || true
    fi
  fi
  docker rm -f "$PW_NAME" >/dev/null 2>&1 || true
  if [ "$STARTED" = real ]; then
    docker compose -f "$ROOT/compose.yaml" down >/dev/null 2>&1 || true
  else
    docker rm -f "$APP_NAME" >/dev/null 2>&1 || true
  fi
}
# dash does not run the EXIT trap on INT or TERM: convert them into an exit.
trap cleanup EXIT
trap 'exit 130' INT TERM

run_suite() {
  # The mount is read-only: pytest works on a copy inside the container.
  docker run --rm --name "$PW_NAME" --network host -e E2E_VIDEO_URL -e E2E_LEVEL \
    -v "$ROOT/e2e":/src/e2e:ro "$PLAYWRIGHT_IMAGE" sh -c '
set -e
mkdir /work && cp -r /src/e2e /work/e2e && cd /work
pip install -q -r e2e/requirements.txt
python -m pytest e2e -p no:cacheprovider
' &
  # background then wait: a signal interrupts wait, a foreground run would delay the trap
  wait $!
}

case "$LEVEL" in
  fake)
    ensure_port_free
    STARTED=fake
    export E2E_LEVEL=fake
    docker build -q -t "$APP_IMAGE" "$ROOT" >/dev/null
    docker run -d --name "$APP_NAME" -e YT_FAKE=1 --network host "$APP_IMAGE" >/dev/null
    wait_for_page
    run_suite
    ;;
  real)
    ensure_port_free
    STARTED=real
    export E2E_LEVEL=real
    docker compose -f "$ROOT/compose.yaml" up -d --build
    # The page is served only once the model is loaded, the first start downloads it.
    wait_for_page 150
    export E2E_VIDEO_URL=https://www.youtube.com/watch?v=KnXm3PbNz5A
    run_suite
    ;;
  *)
    echo "usage: scripts/e2e.sh fake|real" >&2
    exit 2
    ;;
esac
