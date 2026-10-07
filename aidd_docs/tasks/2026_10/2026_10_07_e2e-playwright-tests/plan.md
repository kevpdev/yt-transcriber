---
objective: "The five page scenarios of the MVP review replay with one command, against a fake transcriber without GPU and against the real model."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Playwright e2e tests for the page

## Overview

| Field      | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| **Goal**   | Replay the five hand-made page checks (invalid URL, reload, network cut, 404, copy) at two levels |
| **Source** | GitHub issue kevpdev/yt-transcriber#5                                  |

## Phases

| #   | Phase                                  | File                         |
| --- | -------------------------------------- | ---------------------------- |
| 1   | Fake mode switched by an env variable  | [`phase-1.md`](./phase-1.md) |
| 2   | Playwright suite and GPU-less runner   | [`phase-2.md`](./phase-2.md) |
| 3   | Real-model level and memory update     | [`phase-3.md`](./phase-3.md) |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

| Source | Verified |
| ------ | -------- |
| none   | none     |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| The suite lives in `e2e/` at the repo root, not in `tests/e2e/` (supposed, the issue left it open) | `scripts/check.sh` runs `ruff`, `pyright` and `pytest` on `tests/`, and none of them has Playwright installed. A root folder stays out of the fast gate and the 80 % coverage run with no config change |
| One `YT_FAKE=1` variable swaps both the transcriber and the downloader (supposed, the issue names only the transcriber) | Keeping the real `yt-dlp` would tie the GPU-less level to YouTube and the network. The variable is read only in `build_app`, never set by default, and `compose.yaml` does not pass it |
| The same suite runs at both levels, `E2E_BASE_URL` and `E2E_VIDEO_URL` pick the target | Two copies of five scenarios would drift. The real level keeps the issue's rule that a throwaway mount never replaces the real model |
| `docker run` through `scripts/e2e.sh`, no new Compose service (supposed, the issue left it open) | The `yt-transcriber` service already holds the GPU reservation, and the fake level needs the same image without it. One script covers both, like `scripts/check.sh` |
| `pytest-playwright` inside the official Playwright Python image, run with `--network host` and `--no-sandbox` (supposed, the issue left it open) | Chromium as root needs `--no-sandbox`, as the issue states. The image tag is pinned to the `pytest-playwright` version at implementation time |
