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
scripts/check.sh
```

Enchaîne `ruff format --check`, `ruff check`, `pyright`, puis `pytest` avec un seuil de couverture de 80 %, dans un conteneur `python:3.12-slim`, et s'arrête à la première étape en échec. `scripts/check.sh --fast` s'arrête après `pyright`.

Pour que `git commit` lance les trois premières étapes sur le contenu indexé :

```sh
git config core.hooksPath scripts/hooks
```

### Tests de bout en bout de la page

Cinq contrôles Playwright (URL invalide, rechargement, coupure réseau, job inconnu, copie), dans `e2e/`, rejoués à deux niveaux. Ils sont hors de `scripts/check.sh`.

```sh
scripts/e2e.sh fake   # Docker seul, sans GPU ni YouTube : l'appli tourne avec YT_FAKE=1
scripts/e2e.sh real   # Docker et GPU : le vrai modèle, sur la vidéo KnXm3PbNz5A
```

`fake` construit l'image et lance l'appli avec un transcripteur factice (job d'environ 10 s). `real` lance `docker compose up` et exige le GPU, `nvidia-container-toolkit` et internet (YouTube). Les deux libèrent le port 8000 à la fin.

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
