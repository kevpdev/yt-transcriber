# VCS

The version-control conventions this project follows: branches, commits, and the platform.

## Setup

- Main branch: `main`
- Platform: `github`, repository `kevpdev/yt-transcriber`, driven with `gh`

## Branches

- Format: `type/short-description`, for example `feat/mvp-transcriber`, `docs/ameliorations`
- Types in use: `feat`, `docs`
- Work lands on `main` through a pull request, merged with a merge commit.

## Commits

- Convention: conventional commits
- Format: `type(scope): description`, for example `docs(roadmap): add Playwright e2e tests to the backlog`
- Rules: English, imperative mood, lowercase, no trailing period

## Commit Strategy

AI should auto commit: `never`
