# Review: file d'attente des jobs (#12)

- **Verdict**: approve
- **Diff**: `main...feat/job-queue` (8f0b248)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_14
- **Findings**: 0 critical, 0 warning, 3 minor

## Phases

### Phase 1 — ADR de la file

- [x] `job-queue.md` existe, statut Accepted, avec les sections du modèle — `aidd_docs/memory/internal/decisions/job-queue.md:1-39`
- [x] `stack.md` ne contient plus « Un second job reçoit un message clair » — `aidd_docs/memory/internal/decisions/stack.md:30`, remplacement inscrit en en-tête `stack.md:7`

### Phase 2 — File FIFO et tests

- [x] `JobStore.start()` n'échoue jamais, l'éviction garde les jobs non finis — `app/jobs.py:82-94`, `tests/test_jobs.py:62`, `tests/test_jobs.py:75`
- [x] un second `POST /jobs` répond 202 pendant qu'un job tourne, `/openapi.json` ne publie plus de 409 sur `POST /jobs` — `app/main.py:237`, `tests/test_contract.py:18`, `tests/test_jobs.py:127`
- [x] `scripts/check.sh` passe, avec les tests d'ordre, d'annulation en file, d'horloge et d'éviction — rerun sur 8f0b248 : ruff et pyright verts, 156 passed, coverage 95 % ; second job observé `queued`, puis `transcribing`, puis `done` (`tests/test_jobs.py:147-153`)

### Phase 3 — Mémoire et README

- [x] le README ne promet plus de 409 sur `POST /jobs` — `README.md:80`, `README.md:104-106`, `README.md:129`, `README.md:158` (mesure marquée historique)
- [x] aucun fichier de `aidd_docs/memory/` ne promet de 409 sur `POST /jobs` — `api.md:24-25`, `architecture.md:31`, `project-brief.md:29`, `testing.md:21`, `generation-outside-app.md:47` (pointeur vers `job-queue.md`)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code | 2 | `app/main.py:204` | Le nouveau `store.fail` du filet de `consume` n'est couvert par aucun test (main.py passe de 3 à 4 lignes non couvertes). Sur ce chemin, aucune ligne `runs` n'est écrite, alors que `api.md:27` ne cite que l'échec d'écriture SQLite comme exception à « the `runs` row is written before the job turns `done` or `error` ». | Un test qui fait lever `work` (ex. un `download` qui lève une `BaseException` maison dérivée d'`Exception` hors du `try`, ou un monkeypatch de `store.set_stage`) et asserte `error` ; ajouter ce cas à l'exception de `api.md:27`, ou l'accepter tel quel. |
| 🟢 minor | code | 2 | `app/main.py:205` | Un thread worker par `create_app`, jamais arrêté (56 appels dans `tests/`). Accepté tel quel par le coordinateur. | Aucun. |
| 🟢 minor | rot | - | `aidd_docs/tasks/2026_10/2026_10_14_job-queue/plan.md:3` | `status: pending` alors que les phases sont `done`. Accepté tel quel, l'orchestrateur le pose. | Aucun. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (7/7) |
| Files checked | app/jobs.py, app/main.py, app/static/app.js, tests/test_jobs.py, tests/test_contract.py, README.md, CLAUDE.md, aidd_docs/memory/README.md, aidd_docs/memory/api.md, aidd_docs/memory/architecture.md, aidd_docs/memory/project-brief.md, aidd_docs/memory/testing.md, aidd_docs/memory/forms.md, aidd_docs/memory/internal/decisions/job-queue.md, aidd_docs/memory/internal/decisions/stack.md, aidd_docs/memory/internal/decisions/generation-outside-app.md |
| Unchecked     | none |
| Unplanned     | `app/static/app.js:73-77` (la page n'efface que son propre id, consigné dans `forms.md:14` et `job-queue.md:23`), `aidd_docs/memory/README.md:39` (index des ADR), renforcement de `tests/test_jobs.py:430-440` et `:449-455` |
