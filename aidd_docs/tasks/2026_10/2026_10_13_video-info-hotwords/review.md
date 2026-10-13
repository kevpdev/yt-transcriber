# Review: infos vidéo, export .txt et hotwords modifiables (#10), correctifs de revue

- **Verdict**: approve
- **Diff**: `e4e9bc7...b6b07f4`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_13
- **Findings**: 0 critical, 0 warning, 2 minor

## Phases

### Phase 1 — Infos vidéo publiées par le job dès l'extraction des métadonnées

- [x] Faux de capture sans `on_info` mort (finding #4 de la revue précédente) — `tests/test_frames.py:159,177,182`, `tests/test_jobs.py:256`

### Phase 2 — Hotwords par job et route de la valeur par défaut

- [x] Inchangée par le delta, critères tenus à la revue précédente — `app/main.py:210-219,256-258`

### Phase 3 — Page, e2e, mémoire et README

- [x] Une saisie égale au défaut n'est plus gardée, un nouveau `HOTWORDS` atteint la page — `app/static/app.js:133-136,167-168`, `e2e/test_page.py:237-245`
- [x] Le champ édité reste gardé après rechargement — `app/static/app.js:166`, `e2e/test_page.py:221`
- [x] La reprise d'un job reste la première requête de la page — `app/static/app.js:171-179`
- [x] Révocation du blob différée — `app/static/app.js:217-218`
- [x] `maxlength` relié à `MAX_HOTWORDS` — `app/static/index.html:69`
- [x] `scripts/e2e.sh fake` passe avec le nouveau scénario — rapporté `14 passed`, 14 `def test_` comptés à `b6b07f4`
- [x] Aucune ligne de la mémoire ni du README ne contredit le comportement — `README.md:17,177`, `aidd_docs/memory/forms.md:13`, `aidd_docs/memory/testing.md:30`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | code | 3 | `app/static/app.js:133-136` | Si l'utilisateur soumet avant la réponse de `GET /hotwords`, ou si cette requête échoue, `hotwordsDefault` vaut `null` et le champ encore vide est gardé sous la forme `""`. Le serveur applique bien `HOTWORDS`, mais le champ reste vide à chaque visite au lieu de montrer le défaut. La fenêtre fait quelques millisecondes en local. | Traiter le vide comme le défaut : `if (!hotwords \|\| hotwords === hotwordsDefault) removeItem`. |
| 🟢 | rot | 3 | `aidd_docs/memory/api.md:20-21` | Reporté de la revue précédente (#6), non traité : puces rangées sous « What the schema does not say » pour des champs présents dans le schéma, normalisation décrite trois fois. | Ne garder dans `api.md` que ce que le schéma ne dit pas. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (10/10)                                      |
| Files checked | app/static/app.js, app/static/index.html, e2e/test_page.py, tests/test_frames.py, tests/test_jobs.py, README.md, aidd_docs/memory/forms.md, aidd_docs/memory/testing.md |
| Unchecked     | none                                              |
| Unplanned     | none                                              |
