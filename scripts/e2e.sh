#!/bin/sh
# Tests de bout en bout de la page avec Playwright, sur le faux transcripteur ou sur le vrai modèle.
#   scripts/e2e.sh fake   Docker seul, pas de GPU : l'appli tourne avec YT_FAKE=1.
# Le conteneur Playwright partage le réseau de l'hôte pour joindre localhost:8000.
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
LEVEL=${1:-}
# Même version que e2e/requirements.txt : l'image embarque les navigateurs de cette version.
PLAYWRIGHT_IMAGE=mcr.microsoft.com/playwright/python:v1.63.0-noble
APP_IMAGE=yt-transcriber-e2e
APP_NAME=yt-transcriber-e2e-app

wait_for_page() {
  i=0
  until curl -sf -o /dev/null http://localhost:8000/; do
    i=$((i + 1))
    [ "$i" -gt "${1:-60}" ] && { echo "la page ne répond pas sur :8000" >&2; return 1; }
    sleep 2
  done
}

run_suite() {
  # Le montage est en lecture seule : pytest travaille sur une copie dans le conteneur.
  docker run --rm --network host -e E2E_VIDEO_URL \
    -v "$ROOT/e2e":/src/e2e:ro "$PLAYWRIGHT_IMAGE" sh -c '
set -e
mkdir /work && cp -r /src/e2e /work/e2e && cd /work
pip install -q -r e2e/requirements.txt
python -m pytest e2e -p no:cacheprovider
'
}

case "$LEVEL" in
  fake)
    trap 'docker rm -f "$APP_NAME" >/dev/null 2>&1 || true' EXIT
    docker build -q -t "$APP_IMAGE" "$ROOT" >/dev/null
    docker run -d --rm --name "$APP_NAME" -e YT_FAKE=1 --network host "$APP_IMAGE" >/dev/null
    wait_for_page
    run_suite
    ;;
  *)
    echo "usage: scripts/e2e.sh fake" >&2
    exit 2
    ;;
esac
