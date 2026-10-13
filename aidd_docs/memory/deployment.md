# Deployment

Where the project runs and how it ships: CI/CD, environments, and release.

## Pipeline

- No build or deploy pipeline. On pull requests to `main`, `.github/workflows/ci.yml` runs the jobs `lint` (`scripts/check.sh --fast`), `unit-tests` (`scripts/check.sh --tests`), `e2e` (`scripts/e2e.sh fake`) and `security` (Trivy) on standard runners, without GPU, then the gate `ci`, which fails if any of them did not pass. `ci` is the only check the ruleset requires. `codeql (python)` and `codeql (actions)` run apart (`.github/workflows/codeql.yml`), not required. Dependabot updates weekly (`.github/dependabot.yml`). The image is built and run on the user's machine with `docker compose up --build`.
- One Compose service, one image on `python:3.12-slim` plus the CUDA libraries from pip. Its healthcheck (`compose.yaml`) requests `GET /` in Python, so `docker compose ps` shows `health: starting` while the model loads and `healthy` once uvicorn answers (it opens the port after the lifespan). `start_period` is 10 min for the first model download, `start_interval` 5 s.

## Environments

- Local only, on `http://localhost:8000`.
- The GPU is exposed through `deploy.resources.reservations.devices` in `compose.yaml`, which needs `nvidia-container-toolkit` on the host.
- Settings are environment variables: `HOTWORDS`, `YT_DB` (the SQLite file, default `/data/runs.db`, read by the app but not passed by `compose.yaml`) and `HOST_DOCKER_VERSION` (recorded in the run telemetry, empty unless the host passes it, the container has no Docker socket).
- The named volume `hf-cache` holds the model, `down -v` deletes it. The run history is the repo folder `data/`, bind-mounted on `/data` so a GUI on the host opens `data/runs.db` live. The captured slides sit beside it in `data/frames/<run_id>/`. It is git-ignored, owned by root, and survives `down -v`.
- The app logs to stdout. Compose keeps the container logs with the `local` driver, rotated at 3 files of 10 MB (`logging` in `compose.yaml`), and `down` deletes them.
