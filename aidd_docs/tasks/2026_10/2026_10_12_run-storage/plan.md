---
objective: "Chaque job terminé, réussi ou en erreur, ajoute une ligne à la table `runs` d'une base SQLite sur un volume nommé, avec les six familles de champs de #8, et l'historique survit à `docker compose down` puis `up`."
status: implemented
---

# Plan: Stockage des runs en SQLite

## Overview

| Field      | Value                                                                                                   |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| **Goal**   | Écrire chaque run terminé et sa télémétrie dans la table `runs`                                          |
| **Source** | Issue GitHub kevpdev/yt-transcriber#8, ADR `aidd_docs/memory/internal/decisions/run-storage.md`          |

## Phases

| #   | Phase                                                   | File                         |
| --- | ------------------------------------------------------- | ---------------------------- |
| 1   | Collecter la télémétrie et écrire la table `runs`       | [`phase-1.md`](./phase-1.md) |
| 2   | Volume Compose, persistance vérifiée et mémoire à jour | [`phase-2.md`](./phase-2.md) |

## Resources

| Source                                              | Verified                                                                                                                         |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Image `yt-transcriber-yt-transcriber`, 2026-10-12   | `nvidia-smi` présent dans le conteneur : RTX 5060 Ti, 16311 MiB, driver 580.178.04, CUDA 13.0. `pynvml` et `nvidia-ml-py` absents |
| Même image                                          | aucun `/var/run/docker.sock`, donc la version de Docker n'est pas lisible depuis le conteneur                                     |
| Même image                                          | SQLite 3.46.1, faster-whisper 1.2.1, ctranslate2 4.8.2, av 18.1.0, yt-dlp 2026.8.19 lus par `importlib.metadata`                 |
| Même image                                          | `platform.platform()` rend le noyau de l'hôte, `/etc/os-release` rend la Debian du conteneur, pas l'OS de l'hôte                  |

## Decisions

| Decision                                                                                                   | Why                                                                                                         |
| ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| GPU lu par `nvidia-smi --query-gpu`, une fois au démarrage                                                  | mesuré présent dans l'image, `pynvml` serait une dépendance de plus. Champs `null` sans GPU (tests, `YT_FAKE`) |
| Titre, chaîne et durée lus dans le dictionnaire que `extract_info` rend déjà                                 | aucun appel réseau de plus, #10 n'aura qu'à les afficher                                                      |
| Version de Docker lue dans la variable `HOST_DOCKER_VERSION`, `null` si absente                              | le conteneur n'a pas le socket Docker, mesuré. Le README dit comment la passer                               |
| VRAM de pic non mesurée dans #8                                                                             | demande un échantillonnage pendant le run, hors des six familles de l'issue. Capturée pour une issue séparée |
| Le run porte l'identifiant du job                                                                           | une seule clé à suivre de `POST /jobs` jusqu'à la base                                                       |
| Un échec d'écriture en base ne change pas l'état du job                                                     | la transcription reste rendue à l'utilisateur, l'erreur est écrite dans le log                               |
