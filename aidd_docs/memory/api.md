# API

The HTTP API surface: its style, where the contract lives, and what the schema cannot say.

## Style

- JSON over HTTP with FastAPI. The routes are defined inside `create_app` in `app/main.py`.
- No versioning, routes sit at the root.

## Contract

- `/openapi.json` is the contract: every route, its parameters, the schema of its success and of each error code, and the media type of the bodies that are not JSON. `/docs` renders it. Read them for the fields, not this file.
- The response models live in `app/contract.py`. Routes declare them with `responses=`, never `response_model=`, so they describe the bodies without filtering or re-serializing them. `tests/test_contract.py` fails when a route publishes an empty schema or omits a code, and validates the real bodies against the models (`extra="forbid"`).
- A new route or a changed body updates `app/contract.py` and the `EXPECTED` table of `tests/test_contract.py` in the same change.
- FastAPI adds a `422` with its own validation schema to every route with a path parameter. It never fires, a string path parameter always validates. Kept on purpose, see issue #66.
- The schema gives `level` the default `"text"`, while `JobRequest.level` defaults to `None`. The effect is the same, a null means `text`. Kept on purpose, see issue #66: removing either gap means overriding FastAPI's schema generation for a cosmetic gain.

## What the schema does not say

- Errors are `{"detail": "<message>"}`, written in French for the end user, never a stack trace. The exception is a `POST /jobs` body that is not the expected JSON, which gets the English list of the validation library.
- A second `POST /jobs` gets `409` until the first is `done` or `error`. The `409` carries no id of the running job, the caller retries later. Why one job at a time, the polling and what a restart loses are in `architecture.md`. Runs are the finished jobs, read back from SQLite.
- The server accepts no connection before the model is loaded (lifespan), so a failed connection on `/` means "not ready yet".
- The run id is the job id. The `runs` row is written before the job turns `done` or `error`, so `GET /runs/{id}` answers as soon as polling stops, errors included. The one exception is a failed storage write, logged, which leaves the job `done` and the route `404`.
- A `404` on `GET /jobs/{id}` means the app restarted, since jobs live in memory. The caller stops polling and reads `GET /runs/{id}`.
- A `frames` job can end `done` with an empty `frames` list when the capture failed.
- `POST /jobs` publishes the `text` and `frames` values of `level` in the schema, but types it loosely: a null means `text`, and any other value gets the French `422`, not the one of the validation library.
- Only YouTube URLs are accepted, and the backend rewrites them to the canonical `watch?v=` form before downloading (`app/urls.py`).
- `GET /runs` reads `limit` and `offset` itself, so its `422` stays in French. They are declared in the schema by `openapi_extra`.
- `GET /runs/latest` is the most recent run with state `done`, failed runs are skipped, so it is the caller's run only when there is a single client. `GET /runs` sorts by `started_at`, then insertion order.
- `GET /runs/{id}/frames/{name}` only serves a name listed in the `frames` rows of the run, so the table is the allow-list. An encoded `/` (`..%2Fruns.db`) never reaches the route and gets the generic Starlette `404 {"detail": "Not Found"}`, in English. With `:memory:` there is no image folder and every name is `404`.
- `GET /static/{file}` serves the CSS and JS of the page, outside the schema (a mounted folder).
- The README section « Piloter l'app depuis un agent » is the agent workflow built on these rules, with a script run on the real app. Keep the rules true or update that section.
