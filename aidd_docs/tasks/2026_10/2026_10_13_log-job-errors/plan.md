---
objective: "Un job en échec laisse dans `docker compose logs` son identifiant et sa cause, avec le traceback."
status: implemented
---

# Plan: Journaliser les erreurs de job

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Début, fin et échec de chaque job journalisés sur la sortie standard du conteneur, avec l'identifiant du job |
| **Source** | Issue GitHub kevpdev/yt-transcriber#16 |

## Measure before the change

Sous la configuration de log par défaut d'uvicorn, le logger `app.main` n'a aucun handler : un `info` est perdu, un `error` sort nu par le `lastResort` de `logging`, sans date ni niveau (mesuré dans l'image avec `logging.config.dictConfig(uvicorn.config.LOGGING_CONFIG)`). Les lignes `Could not capture frames` et `Could not record run` existantes sortaient donc déjà, mais sans horodatage.

## Phase 1: logs du job, tests et mémoire

- [x] `app/main.py`, fonction `work` : `log.info` au début (identifiant, URL, niveau) et à la fin (identifiant, état, durée totale).
- [x] `app/main.py`, fonction `work` : `log.exception` dans la branche `AudioError` et dans la branche de l'exception inattendue, avec l'identifiant du job.
- [x] `app/main.py` : `setup_logging()`, appelée par `build_app` seulement, pose un handler sur la sortie standard au niveau `INFO` sur le logger du paquet `app`, une seule fois.
- [x] `tests/test_jobs.py` : un test `caplog` par branche, qui vérifie aussi que `GET /jobs/{id}` garde le message français sans traceback.
- [x] `tests/test_fake.py` : `build_app` pose le handler une seule fois même appelée deux fois.
- [x] `aidd_docs/memory/` et README mis à jour là où ils deviennent faux.

## Decisions

| Decision | Why |
| -------- | --- |
| Handler posé sur le logger `app`, pas sur la racine | n'ajoute pas au flux les logs `INFO` des bibliothèques (faster-whisper, yt-dlp), et laisse uvicorn maître des siens |
| Configuration dans `build_app`, pas dans `create_app` | les tests appellent `create_app` et n'empilent pas de handler, `caplog` capte par propagation |
| `log.exception` aussi pour `AudioError` | demandé par l'issue, le traceback montre l'exception yt-dlp chaînée (`from exc`) |
| Message de `GET /jobs/{id}` inchangé | contrat de `api.md`, le traceback reste dans les logs |

## Validation

- `scripts/check.sh` complet.
- Image de l'app lancée sur un port autre que 8000, en mode factice pour le succès, et avec un téléchargeur qui échoue pour les deux branches d'erreur.
- `scripts/e2e.sh fake` non lancé : il exige le port 8000, tenu par un autre travail, et la page ne change pas.
