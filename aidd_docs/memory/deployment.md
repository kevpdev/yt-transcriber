# Deployment

Where the project runs and how it ships: CI/CD, environments, and release.

## Pipeline

- No build or deploy pipeline, only a Trivy scan on pull requests (`.github/workflows/trivy.yml`) and weekly Dependabot updates (`.github/dependabot.yml`). The image is built and run on the user's machine with `docker compose up --build`.
- One Compose service, one image on `python:3.12-slim` plus the CUDA libraries from pip.

## Environments

- Local only, on `http://localhost:8000`.
- The GPU is exposed through `deploy.resources.reservations.devices` in `compose.yaml`, which needs `nvidia-container-toolkit` on the host.
- `HOTWORDS` is the only setting, passed as an environment variable.
