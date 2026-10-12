---
objective: "Un job marqué « avec images » garde les slides de la vidéo en WebP, horodatées, sans doublon et plafonnées, une ligne par image dans la table `frames`, avec PyAV et sans binaire `ffmpeg`, et la vidéo ne reste pas sur le disque."
status: in-progress
---

# Plan: Capture des slides avec PyAV

## Overview

| Field      | Value                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------- |
| **Goal**   | Télécharger le flux vidéo seul, extraire les slides stables et dédoublonnées, les ranger avec le run                 |
| **Source** | Issue GitHub kevpdev/yt-transcriber#50, ADR `internal/decisions/frames-pyav.md` et `internal/decisions/run-storage.md` |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | Module de capture : téléchargement, détection, dédoublonnage  | [`phase-1.md`](./phase-1.md) |
| 2   | Brancher la capture dans le job et la table `frames`          | [`phase-2.md`](./phase-2.md) |
| 3   | Preuve sur `KnXm3PbNz5A` et mémoire à jour                    | [`phase-3.md`](./phase-3.md) |

## Resources

| Source                                    | Verified                                                                                                                  |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| ADR `frames-pyav.md`, mesures 2026-10-09   | PyAV 18.1.0 de l'image décode `av1`, `vp9`, `h264` et encode `libwebp`. Binaire `ffmpeg` absent                            |
| `uv.lock`                                 | `av` 18.1.0 et `numpy` 2.5.3 déjà verrouillés, `numpy` en dépendance transitive de faster-whisper                          |
| `scripts/check.sh`                        | `uv sync --group dev` installe les dépendances principales, donc `av` et `numpy` sont présents pour pytest sans GPU         |

## Decisions

| Decision                                                                                                         | Why                                                                                                                                         |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Format préféré AV1, puis VP9, puis le meilleur flux vidéo seul ≤ 720p                                              | tranché par l'ADR. La vitesse de décodage reste non mesurée, #53 la mesure                                                                   |
| Détection en numpy, seuils et plafond en constantes nommées de `app/frames.py`                                     | l'ADR la décrit, la comparaison avec le filtre de scène `libavfilter` et le calibrage appartiennent à #53                                     |
| `numpy` déclaré en dépendance directe dans `pyproject.toml`                                                        | le code l'importe, il ne doit plus dépendre d'une dépendance transitive. Aucun paquet système, le `Dockerfile` ne change pas                  |
| La capture est commandée par un drapeau du `JobStore`, `frames=False` par défaut, injectable dans `create_app`, sans champ dans `POST /jobs`    | supposé : #51 porte le champ d'API, le contrôle de la page et l'étape visible. `POST /jobs` reste identique à aujourd'hui                     |
| Images rangées dans `<dossier de la base>/frames/<run_id>/<n>.webp`, chemin relatif au dossier de la base en table | `run-storage.md` : fichiers WebP dans `data/`, la base garde leur chemin. Un chemin relatif survit au montage `./data` vu de l'hôte            |
| La capture passe après la transcription, et son échec laisse le job `done` sans image, avec l'erreur dans le log  | supposé : perdre une transcription de dix minutes pour une image ratée coûte plus que l'absence d'images. #51 pourra rendre l'échec visible     |
| `GET /runs/{id}` rend `frames`, liste de `{position, time, path}`                                                  | le run « garde une liste d'images » lisible sans SQL. Servir les fichiers reste à #52                                                        |
| Preuve réelle par `python -m app.frames <url>` dans l'image, en plus des tests                                      | sans #51 aucun job réel ne peut demander les images par l'API. Le module rejoue exactement la fonction appelée par le job                     |
