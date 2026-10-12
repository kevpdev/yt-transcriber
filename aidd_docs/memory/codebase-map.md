# Codebase Map

The macro layout: the top-level areas and what each holds. A map to navigate, not the full tree.

```mermaid
flowchart TD
    main["app/main.py"] --> urls["app/urls.py"]
    main --> jobs["app/jobs.py"]
    main --> audio["app/audio.py"]
    main --> transcribe["app/transcribe.py"]
    main --> runs["app/runs.py"]
    main --> machine["app/machine.py"]
    main --> frames["app/frames.py"]
    frames --> runs
```

## Areas

- `app/`: the backend. `main.py` wires the routes, `urls.py` validates the YouTube URL, `jobs.py` holds the job state, `audio.py` downloads, `transcribe.py` runs Whisper, `runs.py` writes each finished run to SQLite, reads them back and renders the Markdown view, `frames.py` captures the slides of a video (also run by hand with `python -m app.frames <url> [out_dir]`), `machine.py` reads the machine and the versions once at startup, `fake.py` holds the fake transcriber, downloader and frame capture used when `YT_FAKE=1`.
- `app/static/`: the page, served at `/` and `/static`. `index.html` holds the markup, the Tailwind directives and the theme script of the `<head>`, `theme.css` the theme variables, `app.js` the transcription and the theme button.
- `tests/`: pytest suites for the job flow, the run storage, the URL parsing, the fake mode and the static files, run by `scripts/check.sh`.
- `e2e/`: Playwright scenarios for the page, run by `scripts/e2e.sh fake|real`, outside `scripts/check.sh`.
- `aidd_docs/`: the AI memory, the decision records under `memory/internal/decisions/`, and the task plans.
- Repo root: `Dockerfile`, `compose.yaml`, `entrypoint.sh` for the container, and `scripts/` (`check.sh`, `e2e.sh`).

## Entry points

- `app/main.py`, function `build_app`, started by `uvicorn --factory`.
- `entrypoint.sh`, which sets the CUDA library path and then execs the command.
