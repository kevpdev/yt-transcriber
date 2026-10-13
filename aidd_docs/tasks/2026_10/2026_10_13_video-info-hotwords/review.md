# Review: infos vidéo, export .txt et hotwords modifiables (#10)

- **Verdict**: changes-requested
- **Diff**: `main...feat/video-info-hotwords`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_13
- **Findings**: 1 critical, 2 warning, 3 minor

## Phases

### Phase 1 — Infos vidéo publiées par le job dès l'extraction des métadonnées

- [x] `download_audio` appelle `on_info` avec titre, chaîne (ou uploader) et durée avant tout téléchargement, jamais pour un direct en cours — `app/audio.py:64-69`, `tests/test_audio.py:60-72`
- [x] `GET /jobs/{id}` renvoie `title`, `channel`, `duration` dès `downloading`, `null` avant, corps validé par `JobView` — `app/jobs.py:71-73`, `app/contract.py:55-57`, `tests/test_jobs.py:164-193`

### Phase 2 — Hotwords par job et route de la valeur par défaut

- [x] Le transcriber reçoit les hotwords du job, `GET /runs/{id}` montre la même valeur dans `settings.hotwords` — `app/main.py:127,169`, `tests/test_jobs.py:197-208`
- [x] Sans champ, `null` ou vide, le job utilise `HOTWORDS`, une valeur non textuelle ou trop longue reçoit `422` en français — `app/main.py:210-219`, `tests/test_jobs.py:211-216`
- [x] `GET /hotwords` renvoie `HOTWORDS` lu à l'appel, le schéma publié la décrit — `app/main.py:256-258`, `tests/test_contract.py:21,126`

### Phase 3 — Page, e2e, mémoire et README

- [x] Pendant le job, la page affiche titre, chaîne et durée avant « Terminé » — `app/static/app.js:103`, `e2e/test_page.py:186`
- [x] Le fichier téléchargé a le titre en première ligne et la vue affichée ensuite — `app/static/app.js:204-214`, `e2e/test_page.py:206`
- [x] Le champ est prérempli, garde la saisie après rechargement, le run enregistre la valeur envoyée — `app/static/app.js:155-167`, `e2e/test_page.py:221`
- [x] `scripts/e2e.sh fake` passe avec les nouveaux scénarios — rapporté `13 passed`, 13 `def test_` comptés dans `e2e/test_page.py`
- [ ] Aucune ligne de la mémoire ni du README ne contredit le nouveau comportement — `README.md:32` promet que `HOTWORDS="..." docker compose up` change les hotwords, faux pour la page dès le premier job (voir finding critique)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | fit | 3 | `app/static/app.js:131` | Chaque soumission écrit la valeur du champ dans `localStorage`, y compris la valeur par défaut préremplie. Au rechargement suivant, `prefillHotwords` (`:158`) prend cette copie et n'appelle plus `GET /hotwords`. Scénario : premier job avec le défaut `Claude Code, ...`, puis `HOTWORDS="Spring Boot" docker compose up` : la page renvoie encore `Claude Code, ...` et le serveur l'utilise. `HOTWORDS` cesse d'être le défaut de la page après un seul job, contraire au critère 3 de l'issue et à l'exemple de `README.md:32`. | Ne garder la saisie que si elle diffère du défaut renvoyé par `GET /hotwords`, sinon `localStorage.removeItem(HOTWORDS_KEY)`. |
| 🟡 | functional | 3 | `README.md:32` | Critère « aucune ligne ne contredit » non tenu, conséquence du finding précédent : l'exemple `HOTWORDS=...` est faux pour un navigateur qui a déjà lancé un job. | Se résout avec le correctif de `app.js:131`, sinon documenter que la page garde sa dernière saisie au-dessus de `HOTWORDS`. |
| 🟡 | code | 3 | `app/static/app.js:213` | `URL.revokeObjectURL` est appelé de façon synchrone juste après `link.click()`. Passe sous Chromium (e2e), mais révoquer avant que le navigateur ait lu le blob est un échec connu de certains navigateurs (supposé pour Firefox et Safari, non mesuré ici). | `setTimeout(() => URL.revokeObjectURL(href), 0)` ou plus long. |
| 🟢 | rot | 1 | `tests/test_frames.py:159,177,182`, `tests/test_jobs.py:256` | `on_info=None` ajouté aux faux de `download_video`, de la sélection et de `capture`, dont les vraies signatures (`app/frames.py:40,136`) n'ont pas changé. Paramètre mort qui laisse croire que la capture reçoit les infos. | Retirer `on_info` de ces quatre faux. |
| 🟢 | rot | 3 | `app/static/index.html:69` | `maxlength="500"` recopie `MAX_HOTWORDS` (`app/main.py:34`). Si la borne serveur change, la page tronque en silence à l'ancienne valeur. | Accepter la copie avec un commentaire qui pointe `MAX_HOTWORDS`, ou retirer `maxlength` et laisser le `422` français parler. |
| 🟢 | rot | 3 | `aidd_docs/memory/api.md:20-21` | Les deux puces sont rangées sous « What the schema does not say » alors que `title`, `channel`, `duration` et `hotwords` (avec `maxLength`) sont dans le schéma. La normalisation des hotwords est aussi décrite trois fois (`api.md`, `architecture.md:33`, `README.md:32`). | Garder dans `api.md` seulement ce que le schéma ne dit pas (moment de `on_info`, blanc vaut défaut, `422` français), et pointer depuis `architecture.md`. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 90% (9/10)                                        |
| Files checked | app/audio.py, app/contract.py, app/fake.py, app/jobs.py, app/main.py, app/transcribe.py, app/static/app.js, app/static/index.html, tests/test_audio.py, tests/test_contract.py, tests/test_frames.py, tests/test_jobs.py, tests/test_runs.py, tests/test_static.py, e2e/test_page.py, README.md, aidd_docs/memory/{api,architecture,design,forms,project-brief,testing}.md |
| Unchecked     | Phase 3, critère 5 (mémoire et README sans contradiction) — fix |
| Unplanned     | `on_info=None` ajouté aux faux de capture de `tests/test_frames.py` et `tests/test_jobs.py:256`, hors projection de la phase 1 |
