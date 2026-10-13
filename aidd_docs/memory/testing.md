# Testing

How the project is tested: the layers, the tools, and the conventions. Where tests live and how to run them.

## Strategy

- Unit and API-level tests in `tests/`, run without a GPU and without network.
- `create_app` takes the transcriber and the downloader as arguments, so tests inject fakes and drive the real routes. `tests/test_jobs.py` defines its own `FakeTranscriber` and `fake_download`, and `app/fake.py` holds the pair that `YT_FAKE=1` and `tests/test_fake.py` use, plus `fake_capture` (two synthetic WebP files, after a pause of `FAKE_CAPTURE_DELAY` seconds so the browser sees the `extracting` stage, set to 0 for every test by `tests/conftest.py`). `tests/test_frames.py` runs the frame selection on synthetic numpy images, without PyAV decoding or network.
- Browser end-to-end tests in `e2e/`, at two levels, see the E2E section. The `real` level is the check of the real Whisper model and yt-dlp path, on video `KnXm3PbNz5A`.

## Tools

- `pytest` as the runner.
- FastAPI `TestClient`, backed by `httpx`, for the routes.

## Conventions

- Tests live in `tests/`, one file per module under test (`test_jobs.py`, `test_urls.py`, `test_runs.py`).
- `tests/test_contract.py` guards `/openapi.json`: no route publishes an empty response schema, each route declares the codes of its `EXPECTED` table, and the real bodies validate against the models of `app/contract.py`.
- `create_app` takes a `RunStore`, `RunStore(":memory:")` by default, so tests never write a file.
- Names read as behavior, for example `test_second_job_while_running_gives_409_then_frees`.
- Jobs run in a thread, so tests poll with a `wait_for` helper instead of sleeping a fixed time.

## Run

- `scripts/check.sh`, the commands are in `coding-assertions.md`. CI runs it on pull requests in two jobs, `lint` (`--fast`) and `unit-tests` (`--tests`).

## E2E

- `e2e/` holds fourteen Playwright scenarios (invalid URL, reload during a job, brief network cut, unknown job, copy, timestamps toggle, theme toggle, slides button with the `extracting` stage, cancel button, video info before the job is done, `.txt` button without then with text, hotwords field, default hotwords not kept), the same suite at both levels. `scripts/e2e.sh` forwards `E2E_VIDEO_URL` and `E2E_LEVEL` (`fake` or `real`) to the container. `E2E_BASE_URL` only applies when pytest is run directly against another server.
- `scripts/e2e.sh fake`: Docker only. The app image runs with `YT_FAKE=1`, which swaps in the fake transcriber and downloader (a job takes about 10 s), and a Playwright container drives it.
- `scripts/e2e.sh real`: Docker and the NVIDIA GPU. `docker compose up` runs the real model, the suite targets `KnXm3PbNz5A`.
- `YT_FAKE` is read only in `build_app` and is never set by `compose.yaml`.
- CI (`.github/workflows/ci.yml`) runs `scripts/e2e.sh fake` as its own job, `e2e`, on pull requests, awaited by the gate `ci`. The `real` level never runs in CI, it needs a GPU.
- Outside `scripts/check.sh` on purpose: the check container has no Playwright, so `pyproject.toml` sets pytest `testpaths = ["tests"]`, and `ruff` and `pyright` only cover `app` and `tests`.
- The Playwright image tag and `e2e/requirements.txt` are pinned to the same version (`playwright` 1.63.0, `pytest-playwright` 0.9.0).

## Browser QA

- Entry: `http://localhost:8000`, started with `docker compose up --build`.
- Auth: none.
- State: no fixtures. Jobs live in memory, `docker compose restart` resets them. Finished runs stay in `data/runs.db`, `sudo rm -r data` deletes them.
