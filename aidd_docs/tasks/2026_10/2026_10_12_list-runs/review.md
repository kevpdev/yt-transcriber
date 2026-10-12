# Review: Lister les runs et lire le dernier

- **Verdict**: changes-requested
- **Diff**: `main...feat/list-runs` (f51d3d3, c68e378)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 1 warning, 7 minor

## Phases

### Phase 1 — Lecture des runs, routes, vue Markdown, tests et mémoire

- [x] `RunStore` rend les runs du plus récent au plus ancien, le détail avec ses segments ordonnés, `None` pour un id inconnu — `app/runs.py:152`, `app/runs.py:168`, `app/runs.py:174`
- [x] Après deux runs, `GET /runs/latest` rend le second et `GET /runs` les deux dans l'ordre. `GET /runs/{id}` rend métadonnées, télémétrie et segments, `404` pour un run inconnu — `app/main.py:141`, `app/main.py:155`, `app/main.py:163`, tests `tests/test_runs.py:190`, `tests/test_runs.py:199`, `tests/test_runs.py:213`
- [x] La vue Markdown d'un run rend une ligne `[mm:ss]` par segment — `app/runs.py:94`, `app/main.py:170`, tests `tests/test_runs.py:228`, `tests/test_runs.py:235`
- [x] `scripts/check.sh` passe, couverture au-dessus de 80 % — rejoué dans `python:3.12-slim` : ruff format et check OK, pyright 0 erreur, `64 passed`, `Total coverage: 91.86%`
- [x] `api.md` et le README décrivent les routes `/runs` — `aidd_docs/memory/api.md:14-17`, `README.md:67-70`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | `app/main.py:155` | `GET /runs/latest` rend le dernier run quel que soit son état. Mesuré : après un run `done` puis un run en erreur, `/runs/latest` rend `state: error`, `text: None`, `segments: []`, et `/runs/{id}/markdown` rend `200` avec `"# gsxiFd8AZQU\n\n"`, un transcript vide sans signal d'erreur. Le besoin de l'ADR `run-storage.md` (« le skill de génération relit le dernier run ») n'est pas servi dès qu'un échec suit un succès. | Faire rendre à `/runs/latest` le dernier run `done` (`WHERE state = 'done'` dans `latest_id`), ou ajouter un filtre `state` à `/runs` et `/runs/latest`. Dans les deux cas, écrire le comportement dans `api.md:15` et `README.md:68`, et ajouter un test « succès puis échec ». |
| 🟢 minor | code | 1 | `app/main.py:124` | `int_param` rend `int \| JSONResponse` et chaque appelant teste `isinstance(..., JSONResponse)` (`app/main.py:143`, `app/main.py:146`) : un type de retour sentinelle, sans annotation. | Lever `HTTPException(status_code=422, detail=...)`, que FastAPI rend en `{"detail": "..."}`, et typer le retour `-> int`. Les deux `isinstance` disparaissent. |
| 🟢 minor | code | 1 | `app/main.py:129` | `int(raw)` accepte `1_0`, `+5` et ` 5`. Mesuré : `limit=1_0` rend `200` avec `limit: 10`. | Valider `raw` avec `re.fullmatch(r"-?\d+", raw)` avant `int()`, et ajouter `limit=1_0` au paramétrage de `tests/test_runs.py:261`. |
| 🟢 minor | conform | 1 | `app/main.py:133` | Message utilisateur incorrect en français : « doit être un entier au moins 0 ». | Écrire « un entier supérieur ou égal à {low} ». |
| 🟢 minor | rot | 1 | `aidd_docs/memory/api.md:26` | « The README API section and `app/jobs.py` are the reference » : le contrat `/runs` vit dans `app/main.py` et `app/runs.py`, la ligne devient plus fausse avec ce diff. | Remplacer `app/jobs.py` par `app/main.py`, où sont toutes les routes. |
| 🟢 minor | rot | 1 | `aidd_docs/memory/codebase-map.md:17` | « `runs.py` writes each finished run to SQLite » : le module lit désormais les runs et rend le Markdown. La tâche 4.3 du plan nomme ce fichier. | « `runs.py` writes each finished run to SQLite, reads them back and renders the Markdown view ». |
| 🟢 minor | fit | 1 | `README.md:40-43` | La section « Lire les derniers runs » passe encore par `docker compose exec … sqlite3`, alors que `GET /runs` existe désormais. | Ajouter `curl localhost:8000/runs/latest` comme voie principale, garder la requête SQL pour la télémétrie. |
| 🟢 minor | code | 1 | `tests/test_runs.py:206` | `isinstance(run["machine"], dict \| None)` accepte `None`, et aucune durée (`download_s`, `transcribe_s`) n'est vérifiée : la « télémétrie » du critère est peu contrainte. | Asserter `run["machine"]` égal à la valeur injectée et `run["transcribe_s"] is not None`. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (5/5) |
| Files checked | app/main.py, app/runs.py, tests/test_runs.py, README.md, aidd_docs/memory/api.md, aidd_docs/memory/codebase-map.md, aidd_docs/memory/architecture.md, aidd_docs/memory/internal/decisions/run-storage.md, aidd_docs/tasks/2026_10/2026_10_12_list-runs/plan.md, aidd_docs/tasks/2026_10/2026_10_12_list-runs/phase-1.md |
| Unchecked     | none |
| Unplanned     | `aidd_docs/tasks/2026_10/2026_10_12_list-runs/backlog-link.json` (lien vers #49, artefact du skill de plan) |
