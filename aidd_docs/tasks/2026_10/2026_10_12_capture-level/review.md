# Review: capture-level (#51)

- **Verdict**: approve, after the fixes of 922a79f and ed2a739 (first pass: changes-requested)
- **Diff**: `main...feat/capture-level` (edb0a17, a878c7d, 2e426d5)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 1 warning, 5 minor

## Phases

### Phase 1 — Niveau par job côté API, run et étape `extracting`

- [x] `JobStore()` ne prend plus d'argument, `start(frames=True)` crée un job qui capture — `app/jobs.py:46`, `app/jobs.py:51`
- [x] `POST /jobs` sans `level` répond `202`, `level: "video"` répond `422 {"detail": "<français>"}` — `app/main.py:35`, `app/main.py:138-141`, `tests/test_jobs.py` `test_unknown_level_gives_422_in_french_and_takes_no_job`
- [x] un job `frames` passe par `extracting` avant `done`, un job `text` jamais — `app/main.py:83-84`, tests `test_job_with_frames_level_passes_through_extracting_and_records_it` et `test_job_without_level_never_extracts_and_records_level_text`
- [x] une base en version 3 s'ouvre en version 4 sans perte, `level = 'text'` sur les anciens runs — `app/runs.py:151-152`, `tests/test_runs.py:375-390`
- [x] `fake_capture` attend 3 s en `YT_FAKE=1`, 0 s dans pytest — `app/fake.py:22`, `app/fake.py:51`, `tests/conftest.py:7-9`
- [x] `scripts/check.sh` passe, couverture au-dessus de 80 % — relancé : `97 passed`, `Total coverage: 91.84%`

### Phase 2 — Case dans la page, scénario Playwright, mémoire et README

- [x] la case est visible sous le champ URL, décochée au chargement, lisible dans les deux thèmes — `app/static/index.html:59-62` (`basis-full`, jeton `text-ink`, `accent-action`), assertion `not_to_be_checked` dans `e2e/test_page.py`
- [x] case cochée, le statut passe par « Extraction des images », case décochée inchangée — `app/static/app.js:21`, `app/static/app.js:109`
- [x] `scripts/e2e.sh fake` passe avec huit scénarios — relancé : `8 passed in 57.94s`
- [x] aucun fichier de mémoire ni le README ne décrit encore `JobStore(frames=True)` ou un choix « à venir avec #51 » — grep vide sur `JobStore(frames` et `#51` hors `internal/decisions/` (voir la ligne `conform` de `frames-pyav.md:56`, qui sort du critère littéral)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | `app/main.py:35` | `{"url": ..., "level": null}` ou `"level": 1` renvoie un 422 pydantic `{"detail": [{"type": "string_type", ..., "msg": "Input should be a valid string"}]}`, en anglais et en liste. Mesuré par sonde `TestClient`. Contredit `api.md` (« Errors are `{"detail": "<message>"}`, written in French ») et la décision du plan qui écarte `Literal` pour garder un `detail` français. Un agent, cible nommée par l'issue, envoie volontiers `null` pour « par défaut ». Le défaut existe déjà pour `url`, le nouveau champ en hérite | déclarer `level: str \| None = None` et traiter `None` comme `"text"` avant le test `in LEVELS`, plus un test `level: None` qui attend `202` |
| 🟢 minor | code | 1 | `app/main.py:83-85` | deux `if job.frames` consécutifs, le second répète la condition du premier | imbriquer : `if job.frames:` puis `set_stage` et `if runs.frames_dir:` dedans |
| 🟢 minor | rot | 1 | `app/runs.py:179` | le défaut `text` vit à trois endroits : `DEFAULT 'text'` SQL (`app/runs.py:73`), `setdefault` Python, et le calcul de `app/main.py:102`. Le `setdefault` ne sert qu'aux 5 appels `record` des tests qui omettent `level`, parce que `values` passe `None` explicitement et casse le `NOT NULL` | garder un seul défaut : soit retirer le `setdefault` et passer `level="text"` dans les appels de test, soit ne construire `INSERT` qu'avec les colonnes fournies pour laisser jouer le `DEFAULT` SQL |
| 🟢 minor | conform | 2 | `aidd_docs/memory/internal/decisions/frames-pyav.md:56` | « Choix supposé : #51 pourra décider de l'afficher à l'utilisateur. » reste au futur, alors que #51 a tranché (plan, décision « Un échec de capture laisse toujours le job `done` sans images ») | réécrire au passé : #51 a reconduit le choix, le rendre visible reste hors périmètre |
| 🟢 minor | conform | 2 | `README.md:17-18` | la section « Utiliser » liste les étapes « (téléchargement, transcription) » et ne cite pas la case « Capturer les images » ni l'extraction | ajouter une étape facultative « coche Capturer les images » et `extraction` à la liste des étapes |
| 🟢 minor | fit | 2 | `app/static/app.js:126-131` | à la reprise après rechargement, `#frames` est décoché quel que soit le niveau du job en cours, `GET /jobs/{id}` n'expose pas le niveau. Le statut « Extraction des images » reste juste, seule la case ment | soit exposer `level` dans `GET /jobs/{id}` et cocher la case à la reprise, soit l'accepter et l'écrire dans `forms.md` |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (10/10)                                      |
| Files checked | app/main.py, app/jobs.py, app/runs.py, app/fake.py, app/static/app.js, app/static/index.html, tests/conftest.py, tests/test_jobs.py, tests/test_runs.py, e2e/test_page.py, README.md, aidd_docs/memory/api.md, aidd_docs/memory/forms.md, aidd_docs/memory/architecture.md, aidd_docs/memory/testing.md, aidd_docs/memory/project-brief.md, aidd_docs/memory/internal/decisions/frames-pyav.md, aidd_docs/memory/internal/decisions/run-storage.md |
| Unchecked     | none                                              |
| Unplanned     | `RunStore.record` `setdefault("level", "text")` (`app/runs.py:179`), `create_app` sans paramètre `jobs` (permis par la tâche 2.4 de phase 1), fixture autouse `tests/conftest.py` (permise par la projection de phase 1) |

## Second pass

- Every finding is fixed, except the `setdefault` of `app/runs.py`, which was kept with its reason: it keeps `record` callable without `level`, and the SQL `DEFAULT` is required by the `ALTER TABLE ... NOT NULL`.
- `scripts/check.sh`: `101 passed`, `Total coverage: 91.87%`. The page and `e2e/` did not change after the e2e run (`8 passed`).
- Challenge against #51: 85 % confidence, no deal breaker. Remaining suggestions: log a skipped capture when the database is in memory, and signal a failed capture to the user with #52.
- The `real` e2e level was not run (no GPU in the check). The new scenario assumes the extraction step stays shown for at least one 2 s poll.
