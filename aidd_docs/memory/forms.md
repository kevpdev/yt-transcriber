# Forms

How forms are built and validated across the UI.

## Approach

- One form, `#form` in `app/static/index.html`, with plain JS in `app/static/app.js` and no form or validation library.

## Conventions

- Validation happens only on the server. The page shows the `detail` of a `422` in the `#error` line.
- Two submit buttons set the level sent with the URL: `#go` ("Transcrire") sends `text`, `#go-frames` ("Transcrire avec les slides") sends `frames`. The handler reads `ev.submitter`, so Enter in the URL field submits with `#go`, text only. Both are disabled while a job runs.
- The running job id is kept in `localStorage`, so a reload resumes polling. A `404` clears it.
- The theme choice is kept in `localStorage` under `yt-transcriber-theme`, see `design.md`.
