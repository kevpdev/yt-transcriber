---
status: pending
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Real-model level and memory update

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/
│   └── e2e.sh                         ✏️ add the `real` level
├── README.md                          ✏️ how to run both levels
└── aidd_docs/memory/
    └── testing.md                     ✏️ e2e section, the real path now has a check
```

## User Journey

```mermaid
flowchart TD
  A["scripts/e2e.sh real"] --> B["docker compose up -d --build with the GPU"]
  B --> C["wait until GET / answers, model loaded"]
  C --> D["Playwright container, E2E_VIDEO_URL set to KnXm3PbNz5A"]
  D --> E["five scenarios on the real model"]
```

## Test Scope

<!-- Required for every phase. Keep Setup, Happy path, any qualifying Edge cases, and any required Teardown in this one journey. -->

```mermaid
---
title: Test scope
---
journey
  section Setup
    compose up with the GPU, no YT_FAKE => GET / answers 200 once the model is loaded: 5: cli
  section Happy path
    run the five scenarios on video KnXm3PbNz5A => all pass, transcription takes about 30 s: 5: browser
  section Edge case - fake never active
    compose up without the variable => the job text is a real transcript, not FAKE_TEXT: 1: browser
  section Teardown
    docker compose down => port 8000 free: 5: cli
```

## Tasks to do

### `1)` Real level

> The same suite against the real service, the level the issue says no throwaway mount replaces.

1. `scripts/e2e.sh real`: `docker compose up -d --build`, poll `GET /` (the page is served only after the model loads), run the Playwright container with `E2E_VIDEO_URL=https://www.youtube.com/watch?v=KnXm3PbNz5A`, then `docker compose down` in a `trap`.
2. Run it once on the machine with the GPU and record the duration and the pass count in the issue closing comment.

### `2)` Documentation

> The memory and the README tell the truth about what is tested.

1. `README.md`: the two commands and what each one needs (Docker alone, or Docker with the GPU).
2. `aidd_docs/memory/testing.md`: add an e2e section (`e2e/`, the two levels, `YT_FAKE`, outside `check.sh` and why), and fix the Strategy line that says no test covers the real model path.

## Test acceptance criteria

<!-- Each criterion is an observable behavior, not a command. -->

| Task | Acceptance criteria                                                                          |
| ---- | -------------------------------------------------------------------------------------------- |
| 1    | `scripts/e2e.sh real` passes the five scenarios on `KnXm3PbNz5A` and leaves port 8000 free   |
| 1    | With the stack up without `YT_FAKE`, the final text of a job is not `FAKE_TEXT`              |
| 2    | `README.md` and `testing.md` name both commands and no longer say the real path is unchecked |
