# Review: Stockage des runs en SQLite (#8)

- **Verdict**: changes-requested
- **Diff**: `main...feat/run-storage` (c0f9b7d)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 2 warning, 5 minor

## Phases

### Phase 1 — Collecter la télémétrie et écrire la table `runs`

- [x] Un téléchargement rend le chemin, le titre, la chaîne et la durée, ou `None` — app/audio.py:19-45
- [x] Une transcription rend texte, langue, probabilité, réglages lisibles sans transcrire — app/transcribe.py:18-33, 61-65
- [x] Sans GPU ni `nvidia-smi`, la lecture de la machine rend `None` sans lever — app/machine.py:47-71, tests/test_runs.py `test_machine_reads_return_none_without_nvidia_smi`
- [x] Base neuve à `user_version` 1 et `runs` vide, base existante non modifiée — app/runs.py:62-69, tests/test_runs.py `test_schema_is_created_once_in_a_file_database`, `test_fresh_database_is_empty_at_version_one`
- [x] Un job réussi puis un job en erreur donnent deux lignes avec leur état final — app/main.py:65-93, tests/test_runs.py:45-65 (orchestrator real stack: rows `done` and `error`)
- [x] Une base qui refuse l'écriture laisse le job `done` avec son texte — app/main.py:92-93, tests/test_runs.py `test_record_failure_leaves_the_job_done`
- [x] `scripts/check.sh` termine sans erreur — re-run 2026-10-12: pyright 0 errors, 44 passed, 89.79 %

### Phase 2 — Volume Compose, persistance vérifiée et mémoire à jour

- [x] `docker volume ls` montre le volume des runs — `local yt-transcriber_runs-data`, compose.yaml:11,22
- [x] Job réussi et job en erreur sur la vraie stack donnent deux lignes — orchestrator evidence (KnXm3PbNz5A `done`, aaaaaaaaaaa `error`)
- [x] Après `docker compose down` puis `up`, le nombre de lignes est inchangé — orchestrator evidence (2 rows kept)
- [x] `scripts/e2e.sh fake` passe — orchestrator evidence (6 passed), not re-run
- [x] Aucune ligne de la mémoire ni du README ne dit que les runs sont perdus au redémarrage — aidd_docs/memory/architecture.md:30, testing.md:41, README.md:32

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | app/main.py:60,65-67 | `store.finish` publishes `done` before `runs.record` runs in `finally`, so a client sees `done` while the row does not exist yet. The tests had to add `wait_for_rows` to absorb it (tests/test_runs.py:15). The issue's goal "qu'un agent relise un run passé" (via #49 `GET /runs/latest`) reads a stale latest run right after `done`. | Write the row before `store.finish` / `store.fail` (compute state first), keeping the storage failure swallowed and logged. |
| 🟡 warning | fit | 1 | aidd_docs/tasks/2026_10/2026_10_12_run-storage/plan.md:38 | Plan says peak VRAM (an "À trancher" item of #8) is "Capturée pour une issue séparée". `gh issue list --state all` shows no such issue. The deferral exists nowhere outside the plan. | Open the issue (label `later`) and cite its number in the plan decision. |
| 🟢 minor | code | 1 | app/runs.py:71-72 | `record(**fields)` reads `fields.get(c)`: a mistyped keyword is dropped silently and stores NULL. | Explicit keyword parameters, or reject keys not in `_COLUMNS`. |
| 🟢 minor | rot | 1 | app/runs.py:79 | `query()` executes arbitrary SQL on a production class and has no production caller, only tests. | Let tests open their own read connection, or keep it and state it is the read seam for #49. |
| 🟢 minor | code | 1 | app/runs.py:66-68 | Any `user_version` below 1 replays the v1 `CREATE TABLE`. Correct at v1, but the branch shape will not hold a v2 migration. | At v2, branch per version step. No change needed now. |
| 🟢 minor | rot | 2 | aidd_docs/memory/deployment.md:14 | `YT_DB` is listed as a setting next to `HOTWORDS`, but compose.yaml does not forward it, so `YT_DB=... docker compose up` has no effect. | Say `YT_DB` is read by the app (tests, direct runs), not settable through Compose. |
| 🟢 minor | conform | 2 | aidd_docs/memory/codebase-map.md:19 | The `tests/` line still lists job flow, URL, fake mode and static files, not the run storage and machine suite. | Add the run storage to the line. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (12/12) |
| Files checked | app/audio.py, app/fake.py, app/machine.py, app/main.py, app/runs.py, app/transcribe.py, compose.yaml, tests/test_runs.py, tests/test_jobs.py, tests/test_fake.py, README.md, aidd_docs/memory/architecture.md, codebase-map.md, deployment.md, testing.md |
| Unchecked     | none |
| Unplanned     | none |
