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
2. La page affiche l'étape (téléchargement, transcription, puis extraction des images avec le second bouton) et le pourcentage de la transcription. Dès que yt-dlp connaît la vidéo, une ligne montre son titre, sa chaîne et sa durée, pour vérifier que c'est la bonne avant d'attendre.
3. Le texte arrive dans la grande zone. Le bouton aux deux feuilles superposées le copie, la flèche vers le bas le télécharge en `.txt` (le titre en première ligne, puis la vue affichée).

La langue parlée est détectée automatiquement et le texte sort dans cette langue, sans traduction. Un seul job tourne à la fois, les suivants attendent leur tour dans une file.

Quand un job échoue, la page affiche un message court. La cause complète est dans les journaux du conteneur, `docker compose logs yt-transcriber` : une ligne au début et à la fin de chaque job avec son identifiant, et le traceback de chaque échec. Compose en garde au plus 3 fichiers de 10 Mo, et `docker compose down` les efface.

## Réglages

| Variable   | Défaut                                | Rôle                                           |
| ---------- | ------------------------------------- | ---------------------------------------------- |
| `HOTWORDS` | `Claude Code, Claude, Anthropic, MCP` | termes tech que Whisper doit orthographier juste, valeur par défaut du champ `hotwords` de `POST /jobs` |
| `HOST_DOCKER_VERSION` | vide | version de Docker gardée dans la télémétrie de chaque run, le conteneur ne peut pas la lire seul |

Exemple : `HOTWORDS="Spring Boot, Kubernetes" docker compose up --build`. Chaque job peut aussi porter ses propres hotwords, par le champ `hotwords` de `POST /jobs`, que remplit l'agent appelant (la page n'a pas de champ) (500 caractères au plus, vide ou absent veut dire la valeur par défaut, lue par `GET /hotwords`). La valeur utilisée est enregistrée dans les réglages du run.

## Historique des runs

Chaque job terminé, réussi ou en erreur, ajoute une ligne à la table `runs` d'une base SQLite, `data/runs.db` dans le repo (monté sur `/data` dans le conteneur). La ligne garde la vidéo (identifiant, titre, chaîne, durée), le niveau (`text` ou `frames`), le résultat (état, erreur, texte, mots, caractères, langue), les temps, les réglages du modèle, la machine et les versions. Les segments horodatés d'un run réussi vont dans la table `segments` (`run_id`, `position`, `start`, `end`, `text`). Quand un job capture les images, chaque slide est un fichier WebP dans `data/frames/<run_id>/` et une ligne de la table `frames` (`run_id`, `position`, `time`, `path`, le chemin étant relatif à `data/`). `docker compose down` et `down -v` gardent l'historique, il s'efface avec `sudo rm -r data` (le fichier appartient à root).

### Capturer les slides à la main

Le bouton « Transcrire avec les slides » de la page lance un job qui passe par l'étape `extracting` après la transcription. Les images se téléchargent par l'`url` de chaque slide dans `GET /runs/{id}`. La fonction de capture se lance aussi seule, sans GPU : elle télécharge le flux vidéo seul (720p au plus, AV1 puis VP9), garde un écran stable par slide sans doublon (`MAX_FRAMES` au plus, dans `app/frames.py`), écrit les WebP et supprime la vidéo.

```sh
docker compose run --rm --no-deps yt-transcriber python -m app.frames https://www.youtube.com/watch?v=KnXm3PbNz5A /tmp/frames
```

Pour le suivre en direct dans un GUI, ouvre `data/runs.db` en lecture seule, par exemple dans DBeaver (connexion SQLite) ou DB Browser for SQLite. Les colonnes `settings`, `machine` et `versions` sont du JSON texte, lisible tel quel, et `json_extract(machine, '$.gpu')` en lit un champ.

Pour passer la version de Docker : `HOST_DOCKER_VERSION=$(docker version -f '{{.Server.Version}}') docker compose up --build`.

Pour relire un run et ses images par l'API, voir [Piloter l'app depuis un agent](#piloter-lapp-depuis-un-agent).

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

Le contrat est publié par l'app elle-même : `http://localhost:8000/openapi.json`, lisible dans `http://localhost:8000/docs`. Il donne chaque route, ses paramètres et le schéma de chaque réponse, succès et erreurs.

- On lance un job avec `POST /jobs`, puis on interroge `GET /jobs/{id}` jusqu'à `done` ou `error`. Un seul job tourne à la fois : les suivants répondent `202` aussi et attendent en `queued`, dans l'ordre d'arrivée. `GET /jobs/{id}` publie aussi `title`, `channel` et `duration`, à `null` tant que le téléchargement ne connaît pas la vidéo, et `GET /hotwords` donne la valeur par défaut des hotwords.
- Un job ne garde pas le GPU indéfiniment : il s'arrête en `error` au bout de 15 minutes, ou sur `POST /jobs/{id}/cancel` (`202` accepté, `404` inconnu, `409` déjà fini). L'arrêt est coopératif, il prend effet au prochain point de passage : quelques secondes, ou le temps du premier segment transcrit. Un direct en cours ou programmé est refusé avant tout téléchargement, un direct terminé est accepté.
- Les runs terminés se relisent par `GET /runs`, `GET /runs/latest` (le dernier run réussi), `GET /runs/{id}`, sa vue `GET /runs/{id}/markdown` et ses slides `GET /runs/{id}/frames/{name}`.
- Les erreurs sont `{"detail": "..."}`, en français.

## Piloter l'app depuis un agent

Cette section suffit à un agent, ou au skill qui le pilote, pour transcrire une vidéo sans lire le code. Elle demande `curl` et `jq` sur l'hôte, et l'app écoute sur `http://localhost:8000`.

### Le cycle

1. **Lancer l'app** avec `docker compose up --build -d`. Le modèle se charge avant que le serveur accepte une connexion : tant que `curl` sur `/` échoue, l'app n'est pas prête. `docker compose ps` affiche `health: starting` pendant ce temps, puis `healthy` (le healthcheck interroge `GET /`). Au premier démarrage, le modèle (1,6 Go) est d'abord téléchargé. Si le conteneur s'arrête (`docker compose ps` vide), le modèle n'a pas pu se charger, ses logs disent pourquoi.
2. **Lancer un job** avec `POST /jobs`, le niveau `frames` pour avoir aussi les slides. La réponse `202` donne l'id du job.
3. **Sonder le job** avec `GET /jobs/{id}` toutes les 2 secondes, jusqu'à ce que `stage` vaille `done` ou `error`. Un `404` veut dire que l'app a redémarré : passer à l'étape 4.
4. **Relire le run** avec `GET /runs/{id}`, le même id que le job. La ligne est écrite avant que le job passe à `done` ou `error`, donc elle existe dès que l'étape 3 s'arrête, y compris pour un échec. Seule exception, une écriture en base qui a échoué : elle est dans les logs du conteneur et la route répond `404`. `GET /runs/latest` renvoie le dernier run réussi, qui est le tien si tu es le seul client.
5. **Télécharger les images** : l'`url` de chaque élément de `frames` est une route relative, à préfixer par `http://localhost:8000`.
6. **Arrêter l'app** avec `docker compose down`, jamais `down -v` qui efface le modèle en cache. L'historique dans `data/` survit dans les deux cas.

### Les codes à traiter

Les routes, leurs paramètres et le schéma de chaque réponse sont dans `http://localhost:8000/docs`. Ce tableau dit seulement quoi faire de chaque code.

| Appel | Code | Quoi faire |
| --- | --- | --- |
| `POST /jobs` | `202` | sonder le job |
| `POST /jobs` | `422` | corriger la requête, réessayer ne sert à rien |
| `POST /jobs/{id}/cancel` | `202` | l'arrêt est demandé, continuer à sonder : le job passe en `error` avec « Transcription annulée. », sauf s'il se termine avant le prochain point de passage, auquel cas il finit `done`. L'arrêt peut tarder jusqu'à ~20 s pendant une attente réseau de yt-dlp |
| `POST /jobs/{id}/cancel` | `404` / `409` | job inconnu (redémarrage) / déjà fini : le sondage fait foi |
| `GET /jobs/{id}` | `404` | les jobs vivent en mémoire, un redémarrage les perd. Le run fini reste lisible par `GET /runs/{id}` |
| `GET /runs/{id}` | `404` | id inconnu, job pas encore fini, ou écriture du run échouée |
| `GET /runs/latest` | `404` | aucun run réussi pour l'instant |
| `GET /runs/{id}/frames/{name}` | `404` | run inconnu, nom absent de `frames`, ou fichier effacé du disque |

Les messages sont en français et destinés à un humain, un agent décide sur le code HTTP. Un job qui dépasse 15 minutes finit en `error` avec un message qui cite la limite (sauf pendant la capture des images : la transcription est gardée, sans images), et un direct en cours finit en `error` sans téléchargement. Un job en `done` au niveau `frames` peut avoir `frames` vide : la capture des images a échoué (l'erreur est dans les logs du conteneur) et la transcription est gardée.

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

# 2. lancer : 202 donne l'id, 422 arrête
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
jq -e '.state == "done"' run.json >/dev/null || { jq -r .error run.json; exit 1; }
curl -s "$BASE/runs/latest" | jq -r .id   # le même id si tu es le seul client

# 5. télécharger la première image
FRAME=$(jq -r '.frames[0].url // empty' run.json)
[ -n "$FRAME" ] || { echo "aucune image"; exit 1; }
CODE=$(curl -s -o slide.webp -w '%{http_code}' "$BASE$FRAME")
[ "$CODE" = 200 ] || { echo "GET $FRAME $CODE"; exit 1; }
echo "$FRAME enregistrée dans slide.webp"
```

Joué tel quel le 13 octobre 2026 sur l'app réelle (RTX 5060 Ti, modèle en cache) : 52 s de bout en bout et code de sortie 0, run `done` en français, 3 680 mots, 49 images, la première enregistrée en WebP 1280x720. Mesure historique : à cette date, un second lancement pendant le premier s'arrêtait sur `POST /jobs 409`, avant la file d'attente (#12).

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

Douze contrôles Playwright (URL invalide, rechargement, coupure réseau, job inconnu, copie, bascule de l'horodatage, thème, bouton des slides avec l'étape `extracting`, bouton « Annuler », infos de la vidéo avant la fin du job, bouton `.txt` sans texte puis avec texte), dans `e2e/`, rejoués à deux niveaux. Ils sont hors de `scripts/check.sh`.

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
