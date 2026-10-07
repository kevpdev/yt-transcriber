---
objective: "Python dependencies are declared in pyproject.toml and frozen in uv.lock, and the Trivy scan reads the lock with no resolve step."
status: pending
---

# Plan: uv lockfile

## Overview

| Field      | Value                                                                                 |
| ---------- | ------------------------------------------------------------------------------------- |
| **Goal**   | Replace `requirements*.txt` with `pyproject.toml` and `uv.lock`                       |
| **Source** | GitHub issue kevpdev/yt-transcriber#25, ADR `aidd_docs/memory/internal/decisions/lockfile.md` |

## Phases

| #   | Phase                                   | File                         |
| --- | --------------------------------------- | ---------------------------- |
| 1   | Migrate to uv, then align CI and memory | [`phase-1.md`](./phase-1.md) |

## Resources

| Source                                              | Verified                                                                                         |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| ADR `lockfile.md`, section "Vérifications"          | the Dockerfile recipe built in 2 min and transcribed a 15 min video on GPU in 35 s (2026-10-07)  |
| Trivy `docs/guide/coverage/language/python.md`      | Trivy reads `uv.lock` natively                                                                   |

## Decisions

| Decision                                                  | Why                                                                              |
| --------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `e2e/requirements.txt` stays as is                        | it is installed in the Playwright image, a separate pinned environment, not the app |
| `yt-dlp` upgraded at build after the locked sync          | ADR `lockfile.md`, keeps following YouTube                                       |
