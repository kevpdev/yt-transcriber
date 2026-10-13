# Review: job-limits-cancel (issue #9)

- **Verdict**: approve
- **Diff**: `main...fix/job-limits-cancel` (c075faf..eedf308), repairs `e2dbdaf..eedf308`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_13
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — Limite, annulation et refus des directs côté API

- [x] un job annulé ou hors délai lève `JobStopped` à son prochain `check` — app/jobs.py:50-57 (`cancelled=True` sur l'annulation seulement), tests/test_jobs.py
- [x] une annulation pendant le téléchargement ou la transcription termine le job en `error` en quelques secondes — app/main.py:106-121, tests/test_jobs.py:306-322
- [x] une URL de direct en cours finit en `error` avec un message français lisible, sans téléchargement — app/audio.py:50-55 (faux YoutubeDL seulement, pas de vrai direct mesuré)
- [x] `POST /jobs/{id}/cancel` répond `202`, `404` ou `409` selon l'état, publié dans `/openapi.json` — app/main.py:206-221 (`c.JobCancel`), app/contract.py:36-37, tests/test_contract.py:19,108,113-114
- [x] après une limite dépassée ou une annulation, le `POST /jobs` suivant renvoie `202` — tests/test_jobs.py:362 (limite pendant la capture), 322 (annulation)

### Phase 2 — Bouton « Annuler » de la page et scénario e2e

- [x] « Annuler » n'est visible que pendant un job, et un clic termine le job en `error` avec « Transcription annulée. » — app/static/app.js:45-50,147-160, `scripts/e2e.sh fake` rejoué sur eedf308 : 9 passed
- [x] après l'annulation, une nouvelle transcription démarre sans message de job déjà en cours — app/static/app.js:114 (`cancelling` remis à zéro), e2e 9 passed

### Phase 3 — Healthcheck Compose, mémoire et README

- [x] `docker compose ps` affiche `healthy` seulement après le chargement du modèle — compose.yaml (inchangé depuis la revue précédente, preuve GPU non rejouée)
- [x] la mémoire et le README décrivent la limite, l'annulation, le refus des directs et le healthcheck — README.md:107,114, aidd_docs/memory/api.md:21, architecture.md:31 (forms.md:13 légèrement en retard, voir Findings)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | fit | 1 | app/main.py:116 | Le `job.check()` juste avant `EXTRACTING` lève encore la limite de temps comme une erreur : si les 900 s tombent entre le dernier segment transcrit et ce point de passage, le job `frames` finit `error` et perd une transcription complète, à rebours de la règle de `capture_images` (main.py:76-77). Fenêtre très courte (fin du générateur faster-whisper, transcribe.py:65-73). | Ne laisser passer que l'annulation à ce point (`if job.cancel.is_set()`), ou laisser `capture_images` faire le premier `check`. |
| 🟢 minor | code | 2 | app/static/app.js:151-156 | Course : si la réponse `202` du cancel arrive après qu'un sondage a vu `done` et appelé `stop()`, `cancelling` repasse à `true` et « Annulation… » écrase « Terminé. » jusqu'à la prochaine soumission. Après un rechargement, le cancel en attente n'est plus affiché (état module perdu), retour au comportement d'avant la réparation. | Garder `if (resp.ok && current)` ; le rechargement est acceptable tel quel. |
| 🟢 minor | rot | 1 | tests/test_contract.py:108-111 | Le cancel ajouté avant `gate.set()` fait que le `JobView` final validé n'est un `done` que parce que `FakeTranscriber` ne rappelle plus `on_progress` après la porte (annulation tardive, tests/test_jobs.py:25-34). Un `check()` ajouté après la transcription ferait valider silencieusement un corps `error` à la place, et le `JobView` `done` ne serait plus couvert nulle part. | Valider `JobCancel` sur un second job, ou affirmer `stage == "done"` à la ligne 111. |
| 🟢 minor | rot | 2 | aidd_docs/memory/forms.md:13 | « the polling displays the final `error` » : faux pour une annulation tardive (`done`), et ne dit pas que « Annulation… » reste affiché jusqu'à la fin (drapeau `cancelling`). | Aligner sur api.md:21 en une phrase. |
| 🟢 minor | conform | 1 | issue #9 « Terminé quand » ligne 2 | L'issue dit « Un job qui dépasse la limite passe en `error` ». Pendant la capture il finit désormais `done` sans images. Le plan a été amendé (plan.md:2, « s'arrête »), pas l'issue, et le besoin réel (verrou libéré, `202` ensuite) est tenu. | Le dire dans la PR ou un commentaire de clôture de l'issue. |


## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (9/9) |
| Files checked | app/jobs.py, app/main.py, app/contract.py, app/fake.py, app/audio.py, app/frames.py, app/transcribe.py, app/static/app.js, tests/test_jobs.py, tests/test_contract.py, README.md, aidd_docs/memory/{api,architecture,forms}.md, plan.md, phase-{1,2,3}.md ; `scripts/check.sh` EXIT=0 (ruff, pyright 0 errors, 141 passed, couverture 94,70 %) ; `scripts/e2e.sh fake` 9 passed |
| Unchecked     | none |
| Unplanned     | none |
