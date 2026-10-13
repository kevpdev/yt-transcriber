# Forms

How forms are built and validated across the UI.

## Approach

- One form, `#form` in `app/static/index.html`, with plain JS in `app/static/app.js` and no form or validation library.

## Conventions

- Validation happens only on the server. The page shows the `detail` of a `422` in the `#error` line.
- Two submit buttons set the level sent with the URL: `#go` ("Transcrire") sends `text`, `#go-frames` ("Transcrire avec les slides") sends `frames`. The handler reads `ev.submitter`, so Enter in the URL field submits with `#go`, text only. Both are disabled while a job runs.
- `#hotwords` (label "Hotwords") sits in the form, sent with each job as `hotwords`. It is prefilled with the value kept in `localStorage` under `yt-transcriber-hotwords`, else with `GET /hotwords`, and saved at each submit. Disabled while a job runs. A blank field means the server default.
- `#cancel` ("Annuler") is hidden unless a job runs, and sends `POST /jobs/{id}/cancel`. The status line shows "Annulation…" until the job ends, then the polling displays its final state: `error`, or `done` when the cancel arrived as the job finished. A `404` or `409` on cancel changes nothing, the polling is the authority.
- The running job id is kept in `localStorage`, so a reload resumes polling. A `404` clears it.
- The theme choice is kept in `localStorage` under `yt-transcriber-theme`, see `design.md`.
