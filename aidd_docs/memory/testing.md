# Testing

How the project is tested: the layers, the tools, and the conventions. Where tests live and how to run them.

## Strategy

- Unit and API-level tests only, run without a GPU and without network.
- `create_app` takes the transcriber and the downloader as arguments, so tests inject fakes (`FakeTranscriber`, `fake_download`) and drive the real routes.
- The real Whisper model and the real yt-dlp download are not covered by any test. The README measure on the reference video is the only check of that path.

## Tools

- `pytest` as the runner.
- FastAPI `TestClient`, backed by `httpx`, for the routes.

## Conventions

- Tests live in `tests/`, one file per module under test (`test_jobs.py`, `test_urls.py`).
- Names read as behavior, for example `test_second_job_while_running_gives_409_then_frees`.
- Jobs run in a thread, so tests poll with a `wait_for` helper instead of sleeping a fixed time.

## Run

- `scripts/check.sh`, the commands are in `coding-assertions.md`.

## Browser QA

- Entry: `http://localhost:8000`, started with `docker compose up --build`.
- Auth: none.
- State: no fixtures. Jobs live in memory, `docker compose restart` resets them.
