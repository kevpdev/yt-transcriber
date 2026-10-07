#!/bin/sh
# Tests de bout en bout de la page avec Playwright, sur le faux transcripteur ou sur le vrai modèle.
#   scripts/e2e.sh fake   Docker seul, pas de GPU : l'appli tourne avec YT_FAKE=1.
#   scripts/e2e.sh real   Docker et GPU : compose lance le vrai modèle, vidéo KnXm3PbNz5A.
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

ensure_port_free() {
  if curl -s -o /dev/null --max-time 2 http://localhost:8000/; then
    echo "le port 8000 est déjà utilisé : arrête ce qui répond (docker compose down) avant de lancer les e2e" >&2
    exit 1
  fi
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
    ensure_port_free
    trap 'docker rm -f "$APP_NAME" >/dev/null 2>&1 || true' EXIT
    docker build -q -t "$APP_IMAGE" "$ROOT" >/dev/null
    docker run -d --rm --name "$APP_NAME" -e YT_FAKE=1 --network host "$APP_IMAGE" >/dev/null
    wait_for_page
    run_suite
    ;;
  real)
    ensure_port_free
    trap 'docker compose -f "$ROOT/compose.yaml" down >/dev/null 2>&1 || true' EXIT
    docker compose -f "$ROOT/compose.yaml" up -d --build
    # La page n'est servie qu'une fois le modèle chargé, le premier démarrage le télécharge.
    wait_for_page 150
    export E2E_VIDEO_URL=https://www.youtube.com/watch?v=KnXm3PbNz5A
    run_suite
    ;;
  *)
    echo "usage: scripts/e2e.sh fake|real" >&2
    exit 2
    ;;
esac
