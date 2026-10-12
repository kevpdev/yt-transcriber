# Review: Stockage des runs en SQLite (#8)

- **Verdict**: approve
- **Diff**: `main...feat/run-storage` (514921c)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 0 warning, 4 minor

## Phases

### Phase 1 — Collecter la télémétrie et écrire la table `runs`

- [x] Un téléchargement rend le chemin, le titre, la chaîne et la durée, ou `None` — app/audio.py:19-45
- [x] Une transcription rend texte, langue, probabilité, réglages lisibles sans transcrire — app/transcribe.py:18-33, 61-65
- [x] Sans GPU ni `nvidia-smi`, la lecture de la machine rend `None` sans lever — app/machine.py:47-71, tests/test_runs.py `test_machine_reads_return_none_without_nvidia_smi`
- [x] Base neuve à `user_version` 1 et `runs` vide, base existante non modifiée — app/runs.py:62-69, tests/test_runs.py `test_schema_is_created_once_in_a_file_database`, `test_fresh_database_is_empty_at_version_one`
- [x] Un job réussi puis un job en erreur donnent deux lignes avec leur état final — app/main.py:66-99, tests/test_runs.py:40-60, row written before the job is published (app/main.py:66-95 then 96-99)
- [x] Une base qui refuse l'écriture laisse le job `done` avec son texte — app/main.py:94-97, tests/test_runs.py `test_record_failure_leaves_the_job_done`
- [x] `scripts/check.sh` termine sans erreur — re-run 2026-10-12 on 514921c: pyright 0 errors, 44 passed, 89.71 %

### Phase 2 — Volume Compose, persistance vérifiée et mémoire à jour

- [x] `docker volume ls` montre le volume des runs — `local yt-transcriber_runs-data`, compose.yaml:11,22
- [x] Job réussi et job en erreur sur la vraie stack donnent deux lignes — orchestrator evidence on c0f9b7d (KnXm3PbNz5A `done`, aaaaaaaaaaa `error`), not re-run after 8b57e5a
- [x] Après `docker compose down` puis `up`, le nombre de lignes est inchangé — orchestrator evidence on c0f9b7d (2 rows kept)
- [x] `scripts/e2e.sh fake` passe — orchestrator evidence on 514921c (6 passed), not re-run
- [x] Aucune ligne de la mémoire ni du README ne dit que les runs sont perdus au redémarrage — aidd_docs/memory/architecture.md:30, testing.md:41, README.md:32

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 1 | tests/test_runs.py:73-76 | The caplog polling loop is now dead: the log line is written before `store.finish`, so it exists once `wait_for` returns. The commit removed the same loop for rows but kept this one. | Assert `"Could not record run" in caplog.text` directly, drop the loop and the `time` import if unused. |
| 🟢 minor | code | 1 | app/runs.py:72-74 | The new unknown-column `TypeError` guard has no test (runs.py 1 line missed). In `work()` it is caught and only logged, so a typo would surface only through the success test's column asserts. | Add one test calling `record(..., bogus=1)` and expecting `TypeError`. |
| 🟢 minor | rot | 1 | app/runs.py:82 | `query()` runs arbitrary SQL with no production caller yet. Kept on purpose as the read seam for #49. | None now. Revisit when #49 lands. |
| 🟢 minor | code | 1 | app/runs.py:66-68 | Any `user_version` below 1 replays the v1 `CREATE TABLE`. Correct at v1, kept on purpose. | Branch per version step when v2 arrives. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (12/12) |
| Files checked | app/audio.py, app/fake.py, app/machine.py, app/main.py, app/runs.py, app/transcribe.py, compose.yaml, tests/test_runs.py, tests/test_jobs.py, tests/test_fake.py, README.md, aidd_docs/memory/architecture.md, codebase-map.md, deployment.md, testing.md, aidd_docs/tasks/2026_10/2026_10_12_run-storage/plan.md |
| Unchecked     | none |
| Unplanned     | none |
