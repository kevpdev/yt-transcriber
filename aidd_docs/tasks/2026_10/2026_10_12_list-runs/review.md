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

## Second pass

- **Verdict**: approve
- **Diff**: `main...feat/list-runs` (f51d3d3, c68e378, f91ea2e, 35748b2)
- **Axes run**: code, functional, relevancy, puis challenge
- **Date**: 2026_10_12
- **Findings**: 0 critical, 0 warning, 5 minor
- **Mesures**: `scripts/check.sh` rejoué dans `python:3.12-slim` : ruff OK, pyright 0 erreur, `68 passed`, `Total coverage: 91.74%`. Sonde `TestClient` sur `int_param` : `limit=` et `limit=1&limit=200` rendent `422`, `limit=05` rend `200`, `limit=%D9%A3` (chiffre arabe-indien 3) rend `200` avec `limit: 3`.
- **Décision de l'orchestrateur** : `/runs/latest` rend le dernier run `done`. Elle ne contredit aucun critère de #49, puisque deux runs réussis donnent bien le second.

### Constats de la première passe

| # | Constat | État | Preuve |
| --- | --- | --- | --- |
| 1 | `/runs/latest` rend un run en erreur | corrigé | `app/runs.py:164` (`WHERE state = 'done'`), tests `test_latest_run_skips_a_failed_run_but_list_keeps_it`, `test_latest_run_is_404_when_only_a_failed_run_exists` |
| 2 | `int_param` rend une sentinelle `JSONResponse` | corrigé | `app/main.py:125`, `HTTPException` et retour `-> int` |
| 3 | `int()` accepte `1_0`, `+5` | corrigé | `app/main.py:129`, cas ajoutés à `tests/test_runs.py` (paramétrage 422) |
| 4 | « un entier au moins 0 » | corrigé | `app/main.py:131`, « supérieur ou égal à » |
| 5 | `api.md` pointe vers `app/jobs.py` seul | corrigé | `aidd_docs/memory/api.md:26` |
| 6 | `codebase-map.md` dit que `runs.py` ne fait qu'écrire | corrigé | `aidd_docs/memory/codebase-map.md:17` |
| 7 | README « Lire les derniers runs » passe par `sqlite3` | non traité | `README.md:40-44` inchangé, aucune trace dans 35748b2 |
| 8 | Télémétrie peu contrainte dans le test de détail | corrigé | `tests/test_runs.py`, `machine` et `versions` en `dict`, `transcribe_s` numérique |

### Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 1 | `README.md:40-44` | Constat 7 non traité : la voie documentée pour relire les derniers runs reste `docker compose exec … sqlite3`, alors que `GET /runs` et `/runs/latest` existent. | Ajouter `curl localhost:8000/runs/latest` et `curl localhost:8000/runs/<id>/markdown` comme voie principale, garder la requête SQL pour la télémétrie. |
| 🟢 minor | rot | 1 | `app/main.py:154`, `README.md:67-68` | « terminé » désigne deux choses : `/runs` « liste les runs terminés » (erreurs comprises), mais `/runs/latest` répond « Aucun run terminé. » alors qu'un run en erreur existe. Un agent lit un message faux. | Écrire « Aucun run réussi. » dans `app/main.py:154`, `tests/test_runs.py:221` et `:251`, `README.md:68` et `aidd_docs/memory/api.md:15`. |
| 🟢 minor | rot | 1 | `aidd_docs/tasks/2026_10/2026_10_12_list-runs/phase-1.md:29`, `:67`, `:75`, `plan.md:24-30` | Le plan contredit le code : `404 Aucun run.`, `latest_id()` « du run le plus récent », et la décision « dernier run `done` » n'est consignée dans aucune ligne de `Decisions`. `phase-1.md:2` reste `status: pending` alors que `plan.md:3` dit `implemented`. | Ajouter la décision au tableau `Decisions` de `plan.md`, aligner `phase-1.md:29`, `:67`, `:75`, passer `phase-1.md:2` à `implemented`. |
| 🟢 minor | code | 1 | `app/main.py:129` | `\d` accepte les chiffres Unicode : `limit=%D9%A3` rend `200` avec `limit: 3`. | `re.fullmatch(r"-?[0-9]+", raw)`. |
| 🟢 minor | rot | 1 | `aidd_docs/memory/api.md:26` | « The README API section and `app/main.py` and `app/jobs.py` » : double « and ». | « The README API section, `app/main.py` and `app/jobs.py` are the reference. » |

### Challenge

My confidence level of correctness now: 85%

#### Correctness (100%)
- Les cinq critères de #49 tiennent : ordre et `latest` après deux runs, détail complet et `404`, une ligne `[mm:ss]` par segment, tests des trois routes, `api.md` corrigé.
- Un agent sans id de job relit le dernier transcript en deux appels, `GET /runs/latest` puis `GET /runs/{id}/markdown`. Un échec postérieur ne masque plus le dernier succès, et la liste garde les erreurs avec leur `state`.
- `api.md`, `codebase-map.md` et la section API du README décrivent le code. `architecture.md` et `testing.md` ne deviennent pas faux.

#### Deal breakers
- Aucun.

#### Suggestions (enhancements only)
- Les cinq constats mineurs ci-dessus. Le plus utile à l'agent est le message « Aucun run réussi. », les autres touchent la doc et le plan.
