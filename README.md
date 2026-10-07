# yt-transcriber

Colle l'URL d'une vidéo YouTube, récupère la transcription brute (sans horodatage), copie-la en un clic. Tout tourne en local sur le GPU, sans compte ni quota.

## Lancer

```sh
docker compose up --build
```

Puis ouvre <http://localhost:8000>. Au tout premier démarrage, le modèle `large-v3-turbo` (1,6 Go) est téléchargé dans un volume nommé, la page n'est servie qu'une fois le modèle chargé.

Prérequis : Docker avec Compose, `nvidia-container-toolkit`, un GPU NVIDIA récent (testé sur une RTX 5060 Ti, driver 580), accès à internet (YouTube et le CDN Tailwind).

## Utiliser

1. Colle l'URL de la vidéo et clique sur « Transcrire ».
2. La page affiche l'étape (téléchargement, transcription) et le pourcentage.
3. Le texte arrive dans la grande zone. Le bouton aux deux feuilles superposées le copie.

La langue parlée est détectée automatiquement et le texte sort dans cette langue, sans traduction. Un seul job tourne à la fois, un second reçoit un message clair.

## Réglages

| Variable   | Défaut                                | Rôle                                           |
| ---------- | ------------------------------------- | ---------------------------------------------- |
| `HOTWORDS` | `Claude Code, Claude, Anthropic, MCP` | termes tech que Whisper doit orthographier juste |

Exemple : `HOTWORDS="Spring Boot, Kubernetes" docker compose up --build`.

yt-dlp n'est pas figé. Si YouTube change et que le téléchargement casse, reconstruis l'image : `docker compose build --no-cache`.

## API

- `POST /jobs` avec `{"url": "..."}` renvoie `202 {"id"}`, `422` si l'URL est invalide, `409` si un job tourne déjà.
- `GET /jobs/{id}` renvoie `{stage, progress, text, error}`.

## Tests

```sh
docker run --rm -v "$PWD":/src:ro -w /src python:3.12-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider"
```

## Mesure de référence

Vidéo publique de test : [`gsxiFd8AZQU`](https://www.youtube.com/watch?v=gsxiFd8AZQU), « Claude Code : Tout comprendre en une vidéo », **55 min 59 s**, en français.

| Mesure                                            | Valeur                                 |
| ------------------------------------------------- | -------------------------------------- |
| Téléchargement + transcription, via l'API         | 121 s                                  |
| Même vidéo, via la page (Chromium)                | 94 s                                   |
| Texte obtenu                                      | 14 097 mots, « Claude Code » 90 fois, « Cloud Code » 0 fois |
| Processus sur le GPU (`nvidia-smi`, pendant le run) | `python3.12` du conteneur, 2 080 MiB   |

Modèle déjà en cache, RTX 5060 Ti 16 Go, 6 octobre 2026.
Décisions de stack, modèle et mesures : [`aidd_docs/memory/internal/decisions/stack.md`](aidd_docs/memory/internal/decisions/stack.md).
