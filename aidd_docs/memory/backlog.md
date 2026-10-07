# Backlog

## Supports

| Support | Authority for | Role |
| --- | --- | --- |
| `docs/ameliorations.md` | planned improvements after the MVP | the backlog, one entry per topic |
| `aidd_docs/tasks/` | the plan and phases of a delivered change | one folder per run, `plan.md` plus `phase-N.md` |

## Representation

| Artifact | Support | Native representation |
| --- | --- | --- |
| Improvement | `docs/ameliorations.md` | a numbered `###` entry with objective, reason and principle |
| Plan | `aidd_docs/tasks/` | `<yyyy_mm>/<yyyy_mm_dd>_<slug>/plan.md` |
| Phase | `aidd_docs/tasks/` | `phase-N.md` beside its plan |

## Planning

- Priority: the order of the entries in `docs/ameliorations.md`, which is the order they are meant to be done.

## Relations

- Dependency: an improvement that departs from `docs/adr/0001-stack.md` needs a new ADR before it starts.
