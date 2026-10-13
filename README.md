# yt-transcriber

Colle l'URL d'une vidéo YouTube, récupère la transcription, en texte brut ou horodatée d'un clic, copie-la en un clic. Tout tourne en local sur le GPU, sans compte ni quota.

## Lancer

```sh
docker compose up --build
```

Puis ouvre <http://localhost:8000>. Au tout premier démarrage, le modèle `large-v3-turbo` (1,6 Go) est téléchargé dans un volume nommé, la page n'est servie qu'une fois le modèle chargé.

Prérequis : Docker avec Compose, `nvidia-container-toolkit`, un GPU NVIDIA récent (testé sur une RTX 5060 Ti, driver 580), accès à internet (YouTube et le CDN Tailwind).

## Utiliser

1. Colle l'URL de la vidéo et clique sur « Transcrire », ou sur « Transcrire avec les slides » si tu veux aussi les images.
2. La page affiche l'étape (téléchargement, transcription, puis extraction des images avec le second bouton) et le pourcentage de la transcription.
3. Le texte arrive dans la grande zone. Le bouton aux deux feuilles superposées le copie.

La langue parlée est détectée automatiquement et le texte sort dans cette langue, sans traduction. Un seul job tourne à la fois, un second reçoit un message clair.

## Réglages

| Variable   | Défaut                                | Rôle                                           |
| ---------- | ------------------------------------- | ---------------------------------------------- |
| `HOTWORDS` | `Claude Code, Claude, Anthropic, MCP` | termes tech que Whisper doit orthographier juste |
| `HOST_DOCKER_VERSION` | vide | version de Docker gardée dans la télémétrie de chaque run, le conteneur ne peut pas la lire seul |

Exemple : `HOTWORDS="Spring Boot, Kubernetes" docker compose up --build`.

## Historique des runs

Chaque job terminé, réussi ou en erreur, ajoute une ligne à la table `runs` d'une base SQLite, `data/runs.db` dans le repo (monté sur `/data` dans le conteneur). La ligne garde la vidéo (identifiant, titre, chaîne, durée), le niveau (`text` ou `frames`), le résultat (état, erreur, texte, mots, caractères, langue), les temps, les réglages du modèle, la machine et les versions. Les segments horodatés d'un run réussi vont dans la table `segments` (`run_id`, `position`, `start`, `end`, `text`). Quand un job capture les images, chaque slide est un fichier WebP dans `data/frames/<run_id>/` et une ligne de la table `frames` (`run_id`, `position`, `time`, `path`, le chemin étant relatif à `data/`). `docker compose down` et `down -v` gardent l'historique, il s'efface avec `sudo rm -r data` (le fichier appartient à root).

### Capturer les slides à la main

Le bouton « Transcrire avec les slides » de la page lance un job qui passe par l'étape `extracting` après la transcription. Les images se téléchargent par l'`url` de chaque slide dans `GET /runs/{id}`. La fonction de capture se lance aussi seule, sans GPU : elle télécharge le flux vidéo seul (720p au plus, AV1 puis VP9), garde un écran stable par slide sans doublon (`MAX_FRAMES` au plus, dans `app/frames.py`), écrit les WebP et supprime la vidéo.

```sh
docker compose run --rm --no-deps yt-transcriber python -m app.frames https://www.youtube.com/watch?v=KnXm3PbNz5A /tmp/frames
```

Pour le suivre en direct dans un GUI, ouvre `data/runs.db` en lecture seule, par exemple dans DBeaver (connexion SQLite) ou DB Browser for SQLite. Les colonnes `settings`, `machine` et `versions` sont du JSON texte, lisible tel quel, et `json_extract(machine, '$.gpu')` en lit un champ.

Pour passer la version de Docker : `HOST_DOCKER_VERSION=$(docker version -f '{{.Server.Version}}') docker compose up --build`.

Lire le dernier run réussi et sa transcription horodatée par l'API :

```sh
curl -s localhost:8000/runs/latest
curl -s localhost:8000/runs/<id>/markdown
curl -so 0000.webp localhost:8000/runs/<id>/frames/0000.webp   # une image, URL donnée par `frames[].url`
```

Lire la télémétrie des derniers runs, erreurs comprises :

```sh
docker compose exec yt-transcriber python -c 'import sqlite3; [print(r) for r in sqlite3.connect("/data/runs.db").execute("SELECT started_at, state, title, word_count, transcribe_s FROM runs ORDER BY started_at DESC LIMIT 5")]'
```

Le choix et ses alternatives : [`run-storage.md`](aidd_docs/memory/internal/decisions/run-storage.md).

## Dépendances

Elles sont déclarées dans `pyproject.toml` et figées dans `uv.lock`. Dependabot propose les mises à jour chaque semaine, Trivy scanne le lock à chaque pull request.

| Paquet | Rôle | À savoir |
| --- | --- | --- |
| `fastapi`, `uvicorn` | le serveur HTTP et la page | rien de particulier |
| `faster-whisper` `1.2.1` | transcrit l'audio avec le modèle `large-v3-turbo` sur le GPU | version exacte |
| `av` (PyAV) | décode le fichier audio `.webm` avant la transcription, et la vidéo pour la capture des slides (écrit aussi les WebP), sans installer `ffmpeg` | borné à `>=15,<19`, temporairement : la version 19 casse faster-whisper (`metadata_errors`). La borne saute quand faster-whisper ou PyAV corrige |
| `numpy` | compare les images de la vidéo pour trouver les slides | rien de particulier |
| `yt-dlp` | télécharge la piste audio de la vidéo YouTube, et la piste vidéo seule pour la capture des slides | verrouillé dans `uv.lock`, puis mis à jour au build. Si YouTube change et que le téléchargement casse, reconstruis l'image : `docker compose build --no-cache` |
| `deno` | exécute le JavaScript dont `yt-dlp` a besoin | sans lui, YouTube cache des formats |
| `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` | bibliothèques CUDA appelées par le modèle | groupe `gpu` de `pyproject.toml`, `entrypoint.sh` règle `LD_LIBRARY_PATH` |

Les choix et leurs mesures : [`stack.md`](aidd_docs/memory/internal/decisions/stack.md) pour la stack, [`lockfile.md`](aidd_docs/memory/internal/decisions/lockfile.md) pour le lockfile, [`page-files.md`](aidd_docs/memory/internal/decisions/page-files.md) pour le découpage de la page.

## API

- `POST /jobs` avec `{"url": "...", "level": "text"}` renvoie `202 {"id"}`. `level` est facultatif : `text` (défaut) ou `frames` pour capturer aussi les images. `422` si l'URL ou le niveau est invalide, `409` si un job tourne déjà.
- `GET /jobs/{id}` renvoie `{id, stage, progress, text, segments, error}`. `stage` vaut `queued`, `downloading`, `transcribing`, `extracting` (niveau `frames` seulement), `done` ou `error`. `segments` est la liste des `{start, end, text}` du job terminé (secondes depuis le début), vide tant qu'il n'est pas `done`.
- `GET /runs?limit=&offset=` liste les runs terminés, du plus récent au plus ancien. `limit` de 1 à 100 (20 par défaut), `offset` au moins 0, sinon `422`. Renvoie `{runs, total, limit, offset}`, chaque run étant un résumé (`id, video_id, url, title, channel, video_duration, state, level, language, word_count, started_at, total_s`).
- `GET /runs/latest` renvoie le dernier run réussi (état `done`) en entier, `404 {"detail": "Aucun run réussi."}` s'il n'y en a aucun.
- `GET /runs/{id}` renvoie le run complet (métadonnées, télémétrie, `text`, `segments`, `frames`, la liste des `{position, time, path, url}` des slides, vide sans capture), `404` si l'id est inconnu. `GET /runs/latest` porte aussi `url`.
- `GET /runs/{id}/frames/{name}` renvoie l'image WebP d'un slide (`url` relative donnée par `GET /runs/{id}`). `404 {"detail": "Image inconnue."}` si le nom n'est pas une image du run ou si le fichier a disparu, `404 {"detail": "Run inconnu."}` si l'id est inconnu.
- `GET /runs/{id}/markdown` renvoie le transcript en `text/markdown` : un titre, puis une ligne `[mm:ss] texte` par segment (`[h:mm:ss]` dès une heure).

## Piloter l'app depuis un agent

Cette section suffit à un agent, ou au skill qui le pilote, pour transcrire une vidéo sans lire le code. Elle demande `curl` et `jq` sur l'hôte, et l'app écoute sur `http://localhost:8000`.

### Le cycle

1. **Lancer l'app** avec `docker compose up --build -d`. Le modèle se charge avant que le serveur accepte une connexion : tant que `curl` sur `/` échoue, l'app n'est pas prête. Au premier démarrage, le modèle (1,6 Go) est d'abord téléchargé. Si le conteneur s'arrête (`docker compose ps` vide), le modèle n'a pas pu se charger, ses logs disent pourquoi.
2. **Lancer un job** avec `POST /jobs` et `{"url": "<URL YouTube>", "level": "frames"}`. `level` vaut `text` (défaut, transcription seule) ou `frames` (transcription puis capture des slides). La réponse `202 {"id": "..."}` donne l'id du job.
3. **Sonder le job** avec `GET /jobs/{id}` toutes les 2 secondes, jusqu'à ce que `stage` vaille `done` ou `error`. Les étapes passent par `queued`, `downloading`, `transcribing` (avec `progress` de 0 à 1), puis `extracting` au niveau `frames`. En `error`, le champ `error` porte le message. Un `404` veut dire que l'app a redémarré : passer à l'étape 4.
4. **Relire le run** avec `GET /runs/{id}`, le même id que le job. La ligne est écrite avant que le job passe à `done` ou `error`, donc elle existe dès que l'étape 3 s'arrête, y compris pour un échec (`state` vaut alors `error`). Seule exception, une écriture en base qui a échoué : elle est dans les logs du conteneur et la route répond `404`. `GET /runs/latest` renvoie le dernier run réussi, qui est le tien si tu es le seul client. `GET /runs/{id}/markdown` donne le transcript horodaté.
5. **Télécharger les images** : chaque élément de `frames` porte `position`, `time` (secondes dans la vidéo) et `url`, une route relative à préfixer par `http://localhost:8000`. La réponse est un fichier `image/webp`.
6. **Arrêter l'app** avec `docker compose down`, jamais `down -v` qui efface le modèle en cache. L'historique dans `data/` survit dans les deux cas.

### Les codes à traiter

Les routes et leurs champs sont décrits dans la section API ci-dessus. Ce tableau dit quoi faire de chaque réponse.

| Appel | Code | Corps | Quoi faire |
| --- | --- | --- | --- |
| `POST /jobs` | `202` | `{"id"}` | sonder le job |
| `POST /jobs` | `409` | `{"detail": "Une transcription est déjà en cours, attends qu'elle se termine."}` | un seul job à la fois (un GPU). Réessayer plus tard, l'API ne donne pas l'id du job en cours |
| `POST /jobs` | `422` | `{"detail": "..."}`, une liste au lieu d'un texte si le corps n'est pas un JSON valide | URL qui n'est pas YouTube, `level` autre que `text` ou `frames`, ou corps mal formé. Corriger la requête, réessayer ne sert à rien |
| `GET /jobs/{id}` | `404` | `{"detail": "Job inconnu."}` | les jobs vivent en mémoire, un redémarrage les perd. Le run fini reste lisible par `GET /runs/{id}` |
| `GET /runs/{id}` | `404` | `{"detail": "Run inconnu."}` | id inconnu, job pas encore fini, ou écriture du run échouée |
| `GET /runs/latest` | `404` | `{"detail": "Aucun run réussi."}` | aucun run en état `done` |
| `GET /runs/{id}/frames/{name}` | `404` | `{"detail": "Run inconnu."}` | id de run inconnu |
| `GET /runs/{id}/frames/{name}` | `404` | `{"detail": "Image inconnue."}` | nom absent de `frames` du run, ou fichier effacé du disque |

Les messages sont en français et destinés à un humain, un agent décide sur le code HTTP. Un job en `done` au niveau `frames` peut avoir `frames` vide : la capture des images a échoué (l'erreur est dans les logs du conteneur) et la transcription est gardée.

### Exemple complet

Un script à enregistrer, par exemple sous `transcrire.sh`, et à lancer avec `sh transcrire.sh`. Il s'arrête avec un code non nul sur chaque cas du tableau qui empêche d'aller au bout.

```sh
BASE=http://localhost:8000

# 1. attendre le modèle, 10 minutes au plus
i=0
until curl -s -o /dev/null "$BASE/"; do
  i=$((i + 1)); [ "$i" -lt 120 ] || { echo "app pas prête"; exit 1; }
  sleep 5
done

# 2. lancer : 202 donne l'id, 409 ou 422 arrête
CODE=$(curl -s -o job.json -w '%{http_code}' -X POST "$BASE/jobs" \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=KnXm3PbNz5A", "level": "frames"}')
[ "$CODE" = 202 ] || { echo "POST /jobs $CODE"; cat job.json; exit 1; }
ID=$(jq -r .id job.json)
echo "job $ID"

# 3. sonder jusqu'à done ou error, ou jusqu'à un 404 si l'app a redémarré
while CODE=$(curl -s -o job.json -w '%{http_code}' "$BASE/jobs/$ID"); [ "$CODE" = 200 ]; do
  jq -e '.stage == "done" or .stage == "error"' job.json >/dev/null && break
  sleep 2
done

# 4. relire le run par l'id du job, puis le dernier run réussi
CODE=$(curl -s -o run.json -w '%{http_code}' "$BASE/runs/$ID")
[ "$CODE" = 200 ] || { echo "GET /runs/$ID $CODE"; exit 1; }
jq '{state, error, title, language, word_count, frames: (.frames | length)}' run.json
curl -s "$BASE/runs/latest" | jq -r .id   # le même id si le job a réussi

# 5. télécharger la première image
FRAME=$(jq -r '.frames[0].url // empty' run.json)
[ -n "$FRAME" ] || { echo "aucune image"; exit 1; }
curl -s -o slide.webp -w '%{http_code} %{content_type}\n' "$BASE$FRAME"
```

Joué tel quel le 13 octobre 2026 sur l'app réelle (RTX 5060 Ti, modèle en cache) : 54 s de bout en bout, run `done` en français, 3 680 mots, 49 images, et `200 image/webp` pour la première. Un second lancement pendant le premier s'est arrêté sur `POST /jobs 409`.

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

Sept contrôles Playwright (URL invalide, rechargement, coupure réseau, job inconnu, copie, bascule de l'horodatage, thème), dans `e2e/`, rejoués à deux niveaux. Ils sont hors de `scripts/check.sh`.

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
