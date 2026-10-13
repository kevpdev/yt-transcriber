# Review: job-limits-cancel (issue #9)

- **Verdict**: changes-requested
- **Diff**: `main...fix/job-limits-cancel` (c075faf..e2dbdaf)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_13
- **Findings**: 0 critical, 1 warning, 5 minor

## Phases

### Phase 1 — Limite, annulation et refus des directs côté API

- [x] un job annulé ou hors délai lève `JobStopped` à son prochain `check` — app/jobs.py:44-51, tests/test_jobs.py:979-987
- [x] une annulation pendant le téléchargement ou la transcription termine le job en `error` en quelques secondes — app/main.py:101-117, app/audio.py:46, app/transcribe.py:65-73, tests/test_jobs.py:918-946
- [x] une URL de direct en cours finit en `error` avec un message français lisible, sans téléchargement — app/audio.py:50-55, tests/test_audio.py:682-687 (faux YoutubeDL seulement, pas de vrai direct mesuré)
- [x] `POST /jobs/{id}/cancel` répond `202`, `404` ou `409` selon l'état, publié dans `/openapi.json` — app/main.py:201-216, tests/test_contract.py:21,112-113
- [x] après une limite dépassée ou une annulation, le `POST /jobs` suivant renvoie `202` — tests/test_jobs.py:909-927, 946

### Phase 2 — Bouton « Annuler » de la page et scénario e2e

- [x] « Annuler » n'est visible que pendant un job, et un clic termine le job en `error` avec « Transcription annulée. » — app/static/index.html:63-66, app/static/app.js:44-49,138-154, e2e/test_page.py:166-176
- [x] après l'annulation, une nouvelle transcription démarre sans message de job déjà en cours — e2e/test_page.py:178-183, `scripts/e2e.sh fake` rejoué : 9 passed

### Phase 3 — Healthcheck Compose, mémoire et README

- [x] `docker compose ps` affiche `healthy` seulement après le chargement du modèle — compose.yaml:19-30 (preuve de l'exécutant sur la vraie pile, non rejouée ici : GPU)
- [x] la mémoire et le README décrivent la limite, l'annulation, le refus des directs et le healthcheck — README.md:81,91,107-108,114, aidd_docs/memory/api.md:21, architecture.md:11,31, deployment.md:8, forms.md:13, design.md:15, testing.md:30

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | rot | 1 | app/main.py:75-85, app/jobs.py:19-20 | La limite de 900 s couvre aussi la capture des images. Un job `frames` qui la dépasse pendant `extracting` finit en `error` et perd une transcription déjà réussie, ce qui contredit la règle écrite juste au-dessus (« Losing a transcript for a failed image costs more than having no images »). Le commentaire « About 10 times the longest run measured » ne vaut que pour `text` : dans `data/runs.db`, un run `frames` de 785 s de vidéo a pris 130 s (capture ≈ 98 s), soit une estimation ≈ 510 s pour la vidéo de référence de 56 min, une marge ≈ 1,8× et non 10× (extrapolé, supposé). | Distinguer les deux causes dans `capture_images` : une annulation remonte en `error`, un dépassement de délai pendant la capture garde le job `done` sans images (comme un échec de capture), ou recalculer et documenter la marge pour `frames`. |
| 🟢 minor | fit | 1 | app/jobs.py:84-93, README.md:107 | Course : un cancel arrivé après la sortie du `try` de `work` mais avant `store.finish` reçoit `202`, puis le job finit `done`. Le README affirme sans réserve que le job « passe en `error` avec « Transcription annulée. » ». Le run et le job restent cohérents entre eux. | Nuancer la ligne du README (« sauf s'il se termine avant le prochain point de passage »). |
| 🟢 minor | code | 2 | app/static/app.js:150, app/static/app.js:100-101 | « Annulation… » est écrasé au plus 2 s après par le prochain sondage (« Transcription · 34 % »). Pendant une attente réseau de yt-dlp (jusqu'à 20 s sans hook, `DEFAULT_TIMEOUT = 20` de yt-dlp 2026.08.19), l'utilisateur ne voit plus que l'annulation est en cours. | Garder un drapeau `cancelling` qui préfixe le statut tant que le job n'est pas fini. |
| 🟢 minor | rot | 1 | app/main.py:205 | La réponse `202` du cancel réutilise le modèle `JobCreated`, nommé pour la création : `/openapi.json` publie « JobCreated » pour une annulation. | Accepté si voulu, sinon un alias `JobRef` dans `app/contract.py`. |
| 🟢 minor | rot | 1 | app/fake.py:27,51 | Les faux prennent `lambda: None` par défaut alors que `app/audio.py` exporte `no_check`, déjà réutilisé par `app/frames.py:18`. Le test `tests/test_audio.py:711-712` n'existe que pour couvrir `no_check`. | Importer `no_check` dans `app/fake.py`, supprimer le test de couverture seule. |
| 🟢 minor | rot | - | aidd_docs/tasks/2026_10/2026_10_13_job-limits-cancel/plan.md:3, phase-1.md:2, phase-2.md:2, phase-3.md:2 | Les quatre fichiers de plan gardent `status: pending` alors que les trois phases sont livrées. | Passer le statut à jour. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (9/9) |
| Files checked | app/jobs.py, app/main.py, app/audio.py, app/frames.py, app/transcribe.py, app/fake.py, app/static/app.js, app/static/index.html, compose.yaml, e2e/test_page.py, tests/test_audio.py, tests/test_contract.py, tests/test_fake.py, tests/test_frames.py, tests/test_jobs.py, tests/test_runs.py, README.md, aidd_docs/memory/{api,architecture,deployment,design,forms,testing}.md |
| Unchecked     | none |
| Unplanned     | none |
