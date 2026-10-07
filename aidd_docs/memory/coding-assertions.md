# Coding Assertions

The checks that must pass for code to count as done. Minimal, run after every change.

## Before commit

The fast gate, steps 1 to 3 of `scripts/check.sh --fast`. The pre-commit hook runs it on the staged content.

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `ruff format --check app tests` | formatting |
| 2 | `ruff check app tests` | lint (`E,F,I,UP,B,BLE`) |
| 3 | `pyright` | types |

## Before push

The full chain, `scripts/check.sh`: steps 1 to 3, then step 4.

| Order | Command | Checks |
| ----- | ------- | ------ |
| 4 | `python -m pytest -q -p no:cacheprovider` | the pytest suite, no GPU needed, with the 80 % coverage threshold |

The tools run in a `python:3.12-slim` container on a copy of the repo, `scripts/check.sh` does the setup. It stops at the first failing step.

## Behavior

If a fix is needed, spawn 1 agent per assertion to fix.

## Language

- Code, comments, docstrings, test names and scripts are in English. Documentation (`README.md`, `aidd_docs/`) may be in French.
- User-facing text stays in French: API error messages, page strings, and the fake transcript. Tests that assert those strings keep them as they are.
