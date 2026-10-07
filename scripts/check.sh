#!/bin/sh
# Chaîne de contrôle, du plus déterministe au plus lent, arrêtée à la première étape en échec.
# `--fast` s'arrête après le typecheck (étapes 1 à 3), c'est ce que lance le hook pre-commit.
set -e

ROOT=${CHECK_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
FAST=0
[ "$1" = "--fast" ] && FAST=1

# Le montage est en lecture seule : les outils travaillent sur une copie dans le conteneur.
exec docker run --rm -e FAST="$FAST" -v "$ROOT":/src:ro python:3.12-slim sh -c '
set -e
cp -r /src /work && cd /work
pip install -q -r requirements-dev.txt
echo "1/4 ruff format" && ruff format --check app tests
echo "2/4 ruff check" && ruff check app tests
echo "3/4 pyright" && pyright
[ "$FAST" = 1 ] && exit 0
echo "4/4 pytest" && python -m pytest -q -p no:cacheprovider
'
