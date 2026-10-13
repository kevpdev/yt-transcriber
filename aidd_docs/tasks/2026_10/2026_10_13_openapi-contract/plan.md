---
objective: "`/openapi.json` décrit le succès et les erreurs de chaque route, sans changer une seule réponse."
status: implemented
---

# Plan: Faire de /openapi.json le contrat de l'API

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Un schéma de réponse non vide pour chaque code de chaque route, la doc écrite à la main réduite à ce que le schéma ne dit pas |
| **Source** | Issue GitHub kevpdev/yt-transcriber#64 |

## Measure before the change

FastAPI publie déjà `/openapi.json` et `/docs`. Aucune route n'a de `response_model`, donc chaque `200` et `202` a `schema: {}`. Seul le corps `JobRequest` est typé, et les `404`, `409` et `422` maison ne sont pas déclarés.

## Phase 1: modèles, déclaration, tests et mémoire

- [x] `app/contract.py` : un modèle pydantic par forme de réponse JSON (`Detail`, `JobCreated`, `JobView`, `RunList`, `RunSummary`, `Run`, `Segment`, `FrameOut`), `extra="forbid"`, avec la description des champs que le nom ne dit pas.
- [x] `app/main.py` : chaque route déclare ses codes dans `responses=`, le media type de `/`, `/runs/{id}/markdown` et `/runs/{id}/frames/{name}`, et les paramètres `limit` et `offset` de `GET /runs` via `openapi_extra`.
- [x] `tests/test_contract.py` : chaque réponse de chaque route a un schéma non vide, chaque route déclare les codes attendus, et les corps réels valident contre leur modèle.
- [x] `aidd_docs/memory/api.md`, `codebase-map.md`, `testing.md` et la section API du README renvoient vers `/docs` et `/openapi.json`.

## Decisions

| Decision | Why |
| -------- | --- |
| `responses=` et non `response_model` | `response_model` filtre et re-sérialise les corps à l'exécution. `responses=` ne touche que le schéma publié, donc aucune réponse ne peut changer |
| Les corps réels validés contre les modèles dans les tests, avec `extra="forbid"` | sans `response_model`, rien n'empêche le schéma de dériver du code. Le test le détecte à la place de l'exécution |
| `422` de `POST /jobs` décrit `detail` comme texte ou liste | un corps qui n'est pas du JSON valide reçoit encore la liste d'erreurs de pydantic, le message français couvre l'URL et le niveau |
| `limit` et `offset` documentés par `openapi_extra` | les déclarer en `Query(int)` ferait répondre pydantic en anglais à la place du `422` français |

## Validation

- `scripts/check.sh` complet.
- `/docs` ouvert sur l'app lancée en mode factice (`YT_FAKE=1`), sur un port autre que 8000.
