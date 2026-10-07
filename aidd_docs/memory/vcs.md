# VCS

The version-control conventions this project follows: branches, commits, and the platform.

## Setup

- Main branch: `main`
- Platform: `github`, repository `kevpdev/yt-transcriber`, driven with `gh`

## Branches

- Format: `type/short-description`, for example `feat/mvp-transcriber`, `docs/ameliorations`
- Types in use: `feat`, `docs`
- Work lands on `main` through a pull request, merged with a merge commit.

## Pull request labels

The branch prefix maps to an existing label. A prefix with no row gets no label.

| Prefix | Label |
| --- | --- |
| `feat/` | `enhancement` |
| `fix/`, `hotfix/` | `bug` |
| `docs/` | `documentation` |

## Commits

- Convention: conventional commits
- Format: `type(scope): description`, for example `docs(roadmap): add Playwright e2e tests to the backlog`
- Rules: English, imperative mood, lowercase, no trailing period

## Commit Strategy

AI should auto commit: `only when driven by aidd-orchestrator:01-sdlc, never otherwise`
