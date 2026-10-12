---
objective: "Un agent retrouve par l'API le dernier run, un run choisi ou la liste des runs passés, avec leurs segments et une vue Markdown horodatée, sans connaître l'identifiant du job."
status: reviewed
---

# Plan: Lister les runs et lire le dernier

## Overview

| Field      | Value                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------- |
| **Goal**   | Ouvrir en lecture la table `runs` et ses `segments` par `GET /runs`, `/runs/latest`, `/runs/{id}` |
| **Source** | Issue GitHub kevpdev/yt-transcriber#49, ADR `aidd_docs/memory/internal/decisions/run-storage.md`  |

## Phases

| #   | Phase                                                   | File                         |
| --- | ------------------------------------------------------- | ---------------------------- |
| 1   | Lecture des runs, routes, vue Markdown, tests et mémoire | [`phase-1.md`](./phase-1.md) |

## Decisions

| Decision | Why |
| --- | --- |
| Pagination par `limit` (1 à 100, défaut 20) et `offset` (au moins 0), réponse `{runs, total, limit, offset}` | le plus simple qui pagine, `total` dit à l'agent s'il reste des pages |
| `limit` et `offset` validés à la main, `422 {"detail"}` en français | le contrat d'erreur de `api.md` est `{"detail": "<message>"}`, la validation native de FastAPI rend une liste |
| Ordre `started_at DESC, rowid DESC` | `started_at` est l'ordre voulu par l'issue, `rowid` départage deux runs au même instant |
| La liste rend un résumé par run (sans `text`, sans segments, sans JSON de télémétrie), le détail rend tout | une page de 20 runs de 56 min resterait lourde avec le texte complet |
| Vue Markdown à `GET /runs/{id}/markdown`, `text/markdown`, titre puis une ligne `[mm:ss] texte` par segment, `[h:mm:ss]` dès une heure | l'ADR veut une vue calculée à la demande, le format reprend `formatTime` de `app/static/app.js` |
| `/runs/latest` est déclaré avant `/runs/{id}` | sinon FastAPI lit `latest` comme un identifiant |
| `/runs/latest` rend le run `done` le plus récent, `404 Aucun run réussi.` sinon. `/runs` liste tous les runs, erreurs comprises | un agent relit un transcript, un run en erreur n'en a pas. Décidé par l'orchestrateur après la première revue, l'issue ne tranchait pas |
