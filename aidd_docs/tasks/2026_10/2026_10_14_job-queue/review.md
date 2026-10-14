# Review: file d'attente des jobs (#12)

- **Verdict**: changes-requested
- **Diff**: `main...feat/job-queue`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_14
- **Findings**: 0 critical, 3 warning, 5 minor

## Phases

### Phase 1 — ADR de la file

- [x] `job-queue.md` existe, statut Accepted, avec les sections du modèle — `aidd_docs/memory/internal/decisions/job-queue.md:1-39`
- [x] `stack.md` ne contient plus « Un second job reçoit un message clair » — `aidd_docs/memory/internal/decisions/stack.md:29`

### Phase 2 — File FIFO et tests

- [x] `JobStore.start()` n'échoue jamais, l'éviction garde les jobs non finis — `app/jobs.py:82-94`, `tests/test_jobs.py:62`, `tests/test_jobs.py:75`
- [x] un second `POST /jobs` répond 202 pendant qu'un job tourne, `/openapi.json` ne publie plus de 409 sur `POST /jobs` — `app/main.py:236`, `tests/test_contract.py:18`, `tests/test_jobs.py:127`
- [x] `scripts/check.sh` passe, avec les tests d'ordre, d'annulation en file, d'horloge et d'éviction — rerun : 156 passed, coverage 94.81 %, ruff et pyright verts ; `tests/test_jobs.py:81,127,150,172`

### Phase 3 — Mémoire et README

- [x] le README ne promet plus de 409 sur `POST /jobs` — `README.md:80`, `README.md:104-106`, `README.md:129`, `README.md:158` (mesure marquée historique)
- [x] aucun fichier de `aidd_docs/memory/` ne promet de 409 sur `POST /jobs` — `api.md:24-25`, `architecture.md:31`, `project-brief.md:29`, `testing.md:21` (reste une conséquence d'ADR historique, voir Findings)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 2 | `app/static/app.js:69`, `app/static/app.js:73-77`, `app/static/app.js:142-143` | Régression page à deux onglets, rendue atteignable par la file : la clé `yt-transcriber-job` du `localStorage` est partagée par les onglets. L'onglet B enfile le job 2 et écrase la clé. Quand le job 1 finit dans l'onglet A, `stop()` appelle `remember(null)` et efface l'id du job 2. Un rechargement de A pendant le job 1 reprend le job 2, un rechargement de B après la fin du job 1 ne reprend rien. Avant, B recevait 409 et n'écrivait rien. L'ADR pose « page inchangée (supposé) » sans avoir évalué ce cas. | Ne vider la clé que si elle porte encore l'id du job qui finit (`if (remembered() === id) remember(null)`), et décider en une ligne d'ADR ce que reprend un rechargement quand plusieurs onglets ont un job. |
| 🟡 warning | code | 2 | `tests/test_jobs.py:430`, `tests/test_jobs.py:442` | Les deux tests renommés `..._and_the_next_job_runs` n'assertent qu'un `202` sur le `POST /jobs` suivant. Ce code est désormais inconditionnel, donc l'assertion ne prouve plus rien, et le nom promet un comportement (le job suivant tourne) que le test ne vérifie pas. | Attendre le job suivant avec `wait_for` et asserter `done`, ou rendre aux tests un nom sans cette promesse. |
| 🟡 warning | conform | 1 | `aidd_docs/memory/internal/decisions/stack.md:5-6` | Le contrat demande que le nouvel ADR remplace la promesse de `stack.md`. La convention du fichier inscrit chaque remplacement partiel dans l'en-tête (`Superseded by (partiel)`, lignes 5 et 6). La ligne « Attente côté UI » a été réécrite sur place, sans ligne d'en-tête pour `job-queue.md`, donc l'historique de la décision d'origine est perdu. | Ajouter `- Superseded by (partiel), 2026-10-14: job-queue.md, ligne « Attente côté UI » (le second job recevait un message clair)`. |
| 🟢 minor | code | 2 | `app/main.py:202-203` | Le filet de `consume` journalise mais ne termine pas le job. Si `work` levait hors de son `try` (après `set_stage(DOWNLOADING)`), le job resterait non fini pour toujours : jamais évincé, sondé sans fin par la page et l'agent. | Dans l'`except`, appeler `store.fail(job, "Erreur inattendue pendant la transcription.")`. |
| 🟢 minor | code | 2 | `app/main.py:205` | Un thread worker démarre à chaque `create_app` et ne s'arrête jamais. Environ 56 appels à `create_app` dans `tests/` laissent autant de threads bloqués sur `pending.get()`. Sans effet en production (un seul `build_app`). | Démarrer le worker dans le `lifespan`, ou l'accepter et l'écrire dans `testing.md`. |
| 🟢 minor | functional | 2 | `tests/test_jobs.py:127-147` | Critère d'issue « `GET /jobs/{id}` de la seconde indique qu'elle attend, puis sa progression » : le test observe `queued` puis `done` pour le second job, jamais une étape intermédiaire (`downloading`/`transcribing`). Le chemin est le même que pour le premier job, d'où le statut minor. | Bloquer aussi le second job sur un `Event` et asserter `transcribing` avant `done`. |
| 🟢 minor | rot | 3 | `aidd_docs/memory/internal/decisions/generation-outside-app.md:47` | La conséquence « le refus `409` sera plus fréquent, ce qui donne du poids à la file de #12 » est désormais fausse et ne renvoie pas vers `job-queue.md`. | Ajouter « (résolu par `job-queue.md`) » en fin de ligne. |
| 🟢 minor | rot | - | `aidd_docs/tasks/2026_10/2026_10_14_job-queue/plan.md:3` | `status: pending` alors que les trois phases portent `status: done`. | Passer le plan en `done`. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (7/7) |
| Files checked | app/jobs.py, app/main.py, app/static/app.js, tests/test_jobs.py, tests/test_contract.py, README.md, CLAUDE.md, aidd_docs/memory/README.md, aidd_docs/memory/api.md, aidd_docs/memory/architecture.md, aidd_docs/memory/project-brief.md, aidd_docs/memory/testing.md, aidd_docs/memory/forms.md, aidd_docs/memory/internal/decisions/job-queue.md, aidd_docs/memory/internal/decisions/stack.md, aidd_docs/memory/internal/decisions/generation-outside-app.md |
| Unchecked     | none |
| Unplanned     | `aidd_docs/memory/README.md:39` (index des ADR, cohérent avec `CLAUDE.md`), renommage de `test_job_past_its_time_limit_...` et `test_cancel_during_transcription_...` |
