# Backlog

## Supports

| Support | Authority for | Role |
| --- | --- | --- |
| GitHub Issues | every Task of the backlog | the backlog, independent of branches |
| `aidd_docs/tasks/` | the plan and phases of one delivery run | `plan.md` plus `phase-N.md` per run |
| GitHub Issues, label `later` | ideas kept in reserve | same support, not scheduled, closed or deleted when dropped |

## Representation

A Task is a GitHub issue. The title follows the commit convention: `type(scope): subject`, in English. The type lives only in the title, no type label duplicates it. The labels in use are `later`, for ideas kept in reserve, and `next`, for what is done first.

| Task field | Issue body |
| --- | --- |
| Outcome | `## Objectif`, one verifiable result |
| Scope | `## Périmètre`, one `Inclus` line and one `Exclus` line |
| Done When | `## Terminé quand`, observable checkboxes, each one naming the exact command or observation that proves it |
| Relations | `## Dépend de`, issue numbers, or `rien` |
| Completion Evidence | a comment posted when the issue closes |
| Cancellation | the issue closed with the reason in a comment |

Optional sections, only when they hold something: `## Fichiers à lire` (paths), `## Décisions déjà prises` (a pointer to the ADR), `## À trancher`.

## Workflow

| Support | Native status | Meaning |
| --- | --- | --- |
| GitHub Issues | open | proposed or in progress |
| GitHub Issues | closed | done, or cancelled with a comment saying so |

## Planning

- Priority: the label `next` marks what is done first, an issue with no label is normal, `later` is the reserve. Otherwise the order follows the `Dépend de` links, which say "blocked by" and not "more urgent".

## Relations

- Dependency: written in the body of the issue that depends on another, never copied elsewhere.
- Decision: an issue that departs from `aidd_docs/memory/internal/decisions/stack.md` needs a new ADR before it starts.
