# Deployment

Where the project runs and how it ships: CI/CD, environments, and release.

## Pipeline

- No build or deploy pipeline. On pull requests to `main`, `.github/workflows/ci.yml` runs the jobs `lint` (`scripts/check.sh --fast`), `unit-tests` (`scripts/check.sh --tests`), `e2e` (`scripts/e2e.sh fake`) and `security` (Trivy) on standard runners, without GPU, then the gate `ci`, which fails if any of them did not pass. `ci` is the only check the ruleset requires. `codeql (python)` and `codeql (actions)` run apart (`.github/workflows/codeql.yml`), not required. Dependabot updates weekly (`.github/dependabot.yml`). The image is built and run on the user's machine with `docker compose up --build`.
- One Compose service, one image on `python:3.12-slim` plus the CUDA libraries from pip.

## Environments

- Local only, on `http://localhost:8000`.
- The GPU is exposed through `deploy.resources.reservations.devices` in `compose.yaml`, which needs `nvidia-container-toolkit` on the host.
- `HOTWORDS` is the only setting, passed as an environment variable.
