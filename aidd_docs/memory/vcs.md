# VCS

The version-control conventions this project follows: branches, commits, and the platform.

## Setup

- Main branch: `main`
- Platform: `github`, repository `kevpdev/yt-transcriber`, driven with `gh`

## Branches

- Format: `type/short-description`, for example `feat/mvp-transcriber`, `docs/ameliorations`
- Types in use: `feat`, `docs`, `ci`, `build`, `test`
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

AI should auto commit: `always, on a branch and never on main, then push and open a draft pull request; merge only when the user asks`

- One rule for every change, whatever its size: a one-line fix goes through a branch and a draft pull request like the rest. A size threshold is a judgment that errs, a one-line change can alter what a CI job enforces or the image size.
- The pull request keeps what a commit does not: the why, the measures, the checks and the link to the issue (`Refs #n` or `Closes #n`).
- The merge stays a decision of the user.
