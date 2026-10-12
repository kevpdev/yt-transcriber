# API

The HTTP API surface: its style, the main resources, and the contracts.

## Style

- JSON over HTTP with FastAPI. The routes are defined inside `create_app` in `app/main.py`.
- No versioning, routes sit at the root.

## Resources

- `POST /jobs` takes `{"url": "...", "level": "text"}` and returns `202 {"id"}`. `level` is optional: `text` (default, also for `null`) or `frames`, which also captures the slides. `422` for an invalid URL or an unknown level (`{"detail": "Le niveau doit être text ou frames."}`), `409` when a job is already running.
- `GET /jobs/{id}` returns `{id, stage, progress, text, segments, error}`. `segments` is the list of `{start, end, text}` in seconds, empty until the job is `done`. `404` for an unknown id.
- `GET /runs?limit=&offset=` lists the finished runs, newest first (`started_at`, then insertion order). `limit` is 1 to 100 (default 20), `offset` at least 0, otherwise `422`. Returns `{runs, total, limit, offset}`, each run a summary: `id, video_id, url, title, channel, video_duration, state, level, language, word_count, started_at, total_s`.
- `GET /runs/latest` returns the most recent run with state `done` in full, `404 {"detail": "Aucun run réussi."}` when there is none.
- `GET /runs/{id}` returns every column of the run (`level` included), with `settings`, `machine` and `versions` as objects, `segments` as `{start, end, text}` and `frames` as `{position, time, path, url}` (empty without capture, `path` relative to the database folder, `url` the relative route that serves the image, also on `/runs/latest`). `404 {"detail": "Run inconnu."}` for an unknown id.
- `GET /runs/{id}/markdown` returns `text/markdown; charset=utf-8`: `# <title or video_id>`, then one `[mm:ss] text` line per segment (`[h:mm:ss]` from one hour). Same `404`.
- `GET /runs/{id}/frames/{name}` returns the image as `image/webp`. The name must be the file name of a `frames` row of the run, so the table is the allow-list and `../runs.db` matches nothing. `404 {"detail": "Image inconnue."}` for an unlisted name or a file gone from the disk (and always with `:memory:`), `404 {"detail": "Run inconnu."}` for an unknown run.
- `GET /` serves the page.
- `GET /static/{file}` serves the CSS and JS of the page. `404 {"detail"}` for an unknown file.

## Contracts

- Errors are `{"detail": "<message>"}`, written in French for the end user, never a stack trace.
- `stage` is one of `queued`, `downloading`, `transcribing`, `extracting`, `done`, `error`. `extracting` only exists at level `frames` and has no percentage. `progress` goes from 0 to 1.
- Only YouTube URLs are accepted, and the backend rewrites them to the canonical `watch?v=` form before downloading (`app/urls.py`).
- No OpenAPI spec is maintained. The README API section, `app/main.py` and `app/jobs.py` are the reference.
