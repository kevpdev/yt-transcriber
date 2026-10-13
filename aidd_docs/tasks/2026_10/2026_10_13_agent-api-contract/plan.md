---
objective: "Un agent, ou le skill qui le pilote, sait appeler l'app sans lire son code."
status: implemented
---

# Plan: Documenter le contrat de l'API pour un agent

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Une section du README qui suffit seule à lancer l'app, transcrire, relire le run et télécharger une image, et le même cycle dans `api.md` |
| **Source** | Issue GitHub kevpdev/yt-transcriber#54, dépend de #51 et #52 (fusionnées) |

## Phases

Une seule phase, aucun code ne change.

1. README : section « Piloter l'app depuis un agent » avec le cycle complet (attendre le démarrage, `POST /jobs`, sonder `GET /jobs/{id}`, relire `GET /runs/{id}`, télécharger `frames[].url`), le tableau des codes d'erreur et un script `curl` qui s'exécute tel quel.
2. `aidd_docs/memory/api.md` : section « Agent workflow » qui décrit le même cycle et les invariants sur lesquels il repose.
3. Preuve : sur l'app réelle (GPU), suivre la section seule sur `KnXm3PbNz5A` au niveau `frames`, puis arrêter la pile sans `-v`.

## Decisions

| Decision | Why |
| -------- | --- |
| Le run se relit par l'id du job, `GET /runs/{id}` | `work` écrit la ligne avec `id=job.id` avant de publier `done` ou `error`, donc la ligne existe dès que le job est fini. `/runs/latest` ignore les runs en erreur. |
| La disponibilité se teste en sondant `GET /` | le modèle se charge dans le lifespan et uvicorn n'accepte aucune connexion avant, donc une connexion refusée veut dire « pas prêt » |
| `409` se traite en réessayant plus tard | l'API ne donne pas l'id du job en cours, et il n'y a qu'un GPU |
| `api.md` reste en anglais | tout le fichier l'est, la forme suit le fichier existant |
