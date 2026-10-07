# API

The HTTP API surface: its style, the main resources, and the contracts.

## Style

- JSON over HTTP with FastAPI. The routes are defined inside `create_app` in `app/main.py`.
- No versioning, routes sit at the root.

## Resources

- `POST /jobs` takes `{"url": "..."}` and returns `202 {"id"}`. `422` for an invalid URL, `409` when a job is already running.
- `GET /jobs/{id}` returns `{id, stage, progress, text, error}`. `404` for an unknown id.
- `GET /` serves the page.

## Contracts

- Errors are `{"detail": "<message>"}`, written in French for the end user, never a stack trace.
- `stage` is one of `queued`, `downloading`, `transcribing`, `done`, `error`. `progress` goes from 0 to 1.
- Only YouTube URLs are accepted, and the backend rewrites them to the canonical `watch?v=` form before downloading (`app/urls.py`).
- No OpenAPI spec is maintained. The README API section and `app/jobs.py` are the reference.
