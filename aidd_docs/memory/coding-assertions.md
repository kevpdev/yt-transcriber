# Coding Assertions

The checks that must pass for code to count as done. Minimal, run after every change.

## Before commit

The fast gate.

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `docker run --rm -v "$PWD":/src:ro -w /src python:3.12-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider"` | the pytest suite, no GPU needed |

No linter, formatter or type checker is wired up.

## Behavior

If a fix is needed, spawn 1 agent per assertion to fix.
