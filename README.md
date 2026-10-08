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

## Dépendances

Elles sont déclarées dans `pyproject.toml` et figées dans `uv.lock`. Dependabot propose les mises à jour chaque semaine, Trivy scanne le lock à chaque pull request.

| Paquet | Rôle | À savoir |
| --- | --- | --- |
| `fastapi`, `uvicorn` | le serveur HTTP et la page | rien de particulier |
| `faster-whisper` `1.2.1` | transcrit l'audio avec le modèle `large-v3-turbo` sur le GPU | version exacte |
| `av` (PyAV) | décode le fichier audio `.webm` avant la transcription, sans installer `ffmpeg` | borné à `>=15,<19`, temporairement : la version 19 casse faster-whisper (`metadata_errors`). La borne saute quand faster-whisper ou PyAV corrige |
| `yt-dlp` | télécharge la piste audio de la vidéo YouTube | verrouillé dans `uv.lock`, puis mis à jour au build. Si YouTube change et que le téléchargement casse, reconstruis l'image : `docker compose build --no-cache` |
| `deno` | exécute le JavaScript dont `yt-dlp` a besoin | sans lui, YouTube cache des formats |
| `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` | bibliothèques CUDA appelées par le modèle | groupe `gpu` de `pyproject.toml`, `entrypoint.sh` règle `LD_LIBRARY_PATH` |

Les choix et leurs mesures : [`stack.md`](aidd_docs/memory/internal/decisions/stack.md) pour la stack, [`lockfile.md`](aidd_docs/memory/internal/decisions/lockfile.md) pour le lockfile, [`page-files.md`](aidd_docs/memory/internal/decisions/page-files.md) pour le découpage de la page.

## API

- `POST /jobs` avec `{"url": "..."}` renvoie `202 {"id"}`, `422` si l'URL est invalide, `409` si un job tourne déjà.
- `GET /jobs/{id}` renvoie `{stage, progress, text, error}`.

## Tests

```sh
scripts/check.sh
```

Enchaîne `ruff format --check`, `ruff check`, `pyright`, puis `pytest` avec un seuil de couverture de 80 %, dans un conteneur `python:3.12-slim`, et s'arrête à la première étape en échec. `scripts/check.sh --fast` s'arrête après `pyright`, `scripts/check.sh --tests` ne lance que `pytest`.

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

La CI GitHub lance sur chaque pull request vers `main` les jobs `lint` (`scripts/check.sh --fast`), `unit-tests` (`scripts/check.sh --tests`), `e2e` (`scripts/e2e.sh fake`) et `security` (Trivy), puis la porte `ci`, qui échoue si l'un d'eux échoue et que la branche `main` est seule à exiger. `codeql` (Python et workflows GitHub Actions) tourne à part, non requis. Le niveau `real` reste local.

Docker et `curl` doivent être présents sur l'hôte. `fake` construit l'image et lance l'appli avec un transcripteur factice (job d'environ 10 s). `real` lance `docker compose up` et exige le GPU, `nvidia-container-toolkit` et internet (YouTube). Les deux refusent de démarrer si le port 8000 est pris ou si une pile de l'appli tourne déjà, et libèrent le port à la fin, y compris sur Ctrl-C.

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
