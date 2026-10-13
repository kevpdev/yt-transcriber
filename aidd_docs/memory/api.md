# API

The HTTP API surface: its style, where the contract lives, and what the schema cannot say.

## Style

- JSON over HTTP with FastAPI. The routes are defined inside `create_app` in `app/main.py`.
- No versioning, routes sit at the root.

## Contract

- `/openapi.json` is the contract: every route, its parameters, the schema of its success and of each error code, and the media type of the bodies that are not JSON. `/docs` renders it. Read them for the fields, not this file.
- The response models live in `app/contract.py`. Routes declare them with `responses=`, never `response_model=`, so they describe the bodies without filtering or re-serializing them. `tests/test_contract.py` fails when a route publishes an empty schema or omits a code, and validates the real bodies against the models (`extra="forbid"`).
- A new route or a changed body updates `app/contract.py` and the `EXPECTED` table of `tests/test_contract.py` in the same change.
- FastAPI adds a `422` with its own validation schema to every route with a path parameter. It never fires, a string path parameter always validates.

## What the schema does not say

- Errors are `{"detail": "<message>"}`, written in French for the end user, never a stack trace. The exception is a `POST /jobs` body that is not the expected JSON, which gets the English list of the validation library.
- One job at a time, because there is one GPU: a second `POST /jobs` gets `409` until the first is `done` or `error`. The page polls `GET /jobs/{id}` every 2 s.
- Jobs live in memory, the last 20 are kept and a restart loses them. Runs are the finished jobs, read back from SQLite.
- Only YouTube URLs are accepted, and the backend rewrites them to the canonical `watch?v=` form before downloading (`app/urls.py`).
- `GET /runs` reads `limit` and `offset` itself, so its `422` stays in French. They are declared in the schema by `openapi_extra`.
- `GET /runs/latest` is the most recent run with state `done`, failed runs are skipped. `GET /runs` sorts by `started_at`, then insertion order.
- `GET /runs/{id}/frames/{name}` only serves a name listed in the `frames` rows of the run, so the table is the allow-list. An encoded `/` (`..%2Fruns.db`) never reaches the route and gets the generic Starlette `404 {"detail": "Not Found"}`, in English. With `:memory:` there is no image folder and every name is `404`.
- `GET /static/{file}` serves the CSS and JS of the page, outside the schema (a mounted folder).
