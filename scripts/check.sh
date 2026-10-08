#!/bin/sh
# Check chain, from the most deterministic to the slowest, stopped at the first failing step.
#   1 ruff format --check   formatting
#   2 ruff check            lint
#   3 pyright               types
#   4 pytest                unit and API tests, 80 % coverage threshold
# Everything runs in a python:3.12-slim container: only Docker is needed on the host, locally and in CI.
# `--fast` stops after the typecheck (steps 1 to 3), which is what the pre-commit hook runs.
set -e

ROOT=${CHECK_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
FAST=0
[ "$1" = "--fast" ] && FAST=1

# The mount is read-only: the tools work on a copy inside the container.
exec docker run --rm -e FAST="$FAST" -v "$ROOT":/src:ro python:3.12-slim sh -c '
set -e
cp -r /src /work && cd /work
pip install -q uv==0.12.23
export UV_PROJECT_ENVIRONMENT=/opt/venv VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH
uv sync -q --frozen --group dev
step() {
  title=$1; shift
  echo "::group::$title"
  "$@" && rc=0 || rc=$?
  echo "::endgroup::"
  [ "$rc" = 0 ] || { echo "::error::$title failed"; exit "$rc"; }
}
step "1/4 ruff format" ruff format --check app tests
step "2/4 ruff check" ruff check app tests
step "3/4 pyright" pyright
[ "$FAST" = 1 ] && exit 0
step "4/4 pytest" python -m pytest -q -p no:cacheprovider
'
