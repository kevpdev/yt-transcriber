# Forms

How forms are built and validated across the UI.

## Approach

- One form, `#form` in `app/static/index.html`, with plain JS and no form or validation library.

## Conventions

- Validation happens only on the server. The page shows the `detail` of a `422` in the `#error` line.
- The submit button is disabled while a job runs.
- The running job id is kept in `localStorage`, so a reload resumes polling. A `404` clears it.
