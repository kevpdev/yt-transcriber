# Review: description de la vidéo dans le run

- **Verdict**: approve
- **Diff**: `main...feat/video-description`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_16
- **Findings**: 0 critical, 0 warning, 1 minor

## Phases

### Phase 1 — description du téléchargement jusqu'au run

- [x] `download_audio` rend la description de `info`, ou `None` sans clé — app/audio.py:77, tests/test_audio.py:60-67
- [x] Une base en version 4 s'ouvre en version 5, ses runs gardés, leur description `null` — app/runs.py:156-157, tests/test_runs.py:402-420, live `GET /runs/2c8031b3...` => `description: null`
- [x] `GET /runs/{id}` d'un job fini porte `description`, et le corps valide contre `Run` — app/contract.py:100, app/main.py:158, tests/test_jobs.py:112-117, tests/test_contract.py:144, live run 67420bef... => 1739 car.
- [x] `GET /runs` ne porte pas `description` — app/runs.py `_SUMMARY_COLUMNS` inchangé, tests/test_jobs.py:117, live => `false`
- [x] Aucune phrase de `aidd_docs/memory/` ni du README ne dit « version 4 » pour le schéma courant — aidd_docs/memory/architecture.md:69, grep vide
- [x] `scripts/check.sh` passe — `160 passed`, couverture 94.74 %

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 1 | tests/test_runs.py:165, tests/test_runs.py:231 | `test_two_runs_migration_leaves_the_version_at_four` et `test_fresh_database_is_empty_at_version_four` assertent `(5,)`, alors que les tests voisins ont été renommés `..._to_five` : nom et comportement se contredisent | Renommer sans numéro (`..._at_the_current_version`), ou en `five` comme les voisins |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (6/6) |
| Files checked | app/audio.py, app/contract.py, app/fake.py, app/main.py, app/runs.py, tests/test_audio.py, tests/test_jobs.py, tests/test_runs.py, tests/test_contract.py, README.md, aidd_docs/memory/api.md, aidd_docs/memory/architecture.md, aidd_docs/memory/internal/decisions/run-storage.md |
| Unchecked     | none |
| Unplanned     | none |
