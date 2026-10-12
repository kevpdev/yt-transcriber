# Forms

How forms are built and validated across the UI.

## Approach

- One form, `#form` in `app/static/index.html`, with plain JS in `app/static/app.js` and no form or validation library.

## Conventions

- Validation happens only on the server. The page shows the `detail` of a `422` in the `#error` line.
- The checkbox `#frames` ("Capturer les images") sets the level sent with the URL: `frames` when checked, `text` otherwise. Unchecked by default, and disabled with the submit button while a job runs. After a reload it is unchecked again, even for a running `frames` job, because `GET /jobs/{id}` does not return the level.
- The submit button is disabled while a job runs.
- The running job id is kept in `localStorage`, so a reload resumes polling. A `404` clears it.
- The theme choice is kept in `localStorage` under `yt-transcriber-theme`, see `design.md`.
