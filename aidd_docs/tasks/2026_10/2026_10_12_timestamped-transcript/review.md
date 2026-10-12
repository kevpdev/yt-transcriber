# Review: Transcription horodatée (#48)

- **Verdict**: approve
- **Diff**: `main...feat/timestamped-transcript` (tête `34fa27a`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 0 warning, 1 minor

## Phases

### Phase 1 — Segments dans le transcripteur, le job, l'API et la base

- [x] `Transcriber.run` et `FakeTranscriber.run` rendent des segments dont la jonction est le `text` rendu — `app/transcribe.py:64-73`, `app/fake.py:29-40`, `tests/test_fake.py:38-44`
- [x] `GET /jobs/{id}` d'un job `done` rend `segments` `{start, end, text}` en secondes, `text` inchangé — `app/jobs.py:38`, `app/main.py:98`, `tests/test_jobs.py:73-80`
- [x] Les segments d'un run `done` sont dans la table `segments`, triés par `position` — `app/runs.py:113-116`, `tests/test_runs.py:41-48`
- [x] Une base v1 avec des runs s'ouvre, gagne `segments`, passe en v2 et garde ses runs — `app/runs.py:82-96`, `tests/test_runs.py:61-76`, rejoué sur une copie de `data/runs.db` (6 runs, v1 vers v2, 6 runs conservés, réouverture idempotente, échec de migration laissé en v1 sans état partiel)
- [x] `scripts/check.sh` sort en 0 — rejoué sur `34fa27a` : `52 passed`, `Total coverage: 90.24%`, `check exit 0`

### Phase 2 — Bascule de la page, scénario Playwright et mémoire à jour

- [x] Un clic affiche une ligne `[mm:ss] texte` par segment, un second clic le texte brut — `app/static/app.js:37-41,133-137`, `e2e/test_page.py:106-128`
- [x] Le bouton Copier copie exactement la vue affichée — `app/static/app.js:140`, `e2e/test_page.py:122` lit `navigator.clipboard.readText()` et le compare à la vue horodatée, sauts de ligne compris
- [x] Un début de segment au-delà d'une heure s'affiche `[h:mm:ss]` — `app/static/app.js:25-31`, `e2e/test_page.py:128`
- [x] `scripts/e2e.sh fake` sort en 0 avec le nouveau scénario — rejoué sur `34fa27a` : `7 passed in 43.60s`, `e2e exit 0`
- [ ] `grep -ri "no timestamps\|sans horodatage" README.md aidd_docs/memory` ne rend rien — rend encore `stack.md:6` et `stack.md:10`. Le contexte historique de l'ADR est gardé et marqué remplacé par une ligne datée (`stack.md:6`), donc aucun document vivant n'affirme plus « sans horodatage ». Le besoin est tenu, la lettre du critère non.

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 2 | `aidd_docs/tasks/2026_10/2026_10_12_timestamped-transcript/phase-2.md` (critère 3 de la table) | Le critère grep exige zéro résultat sur `aidd_docs/memory`, alors que la décision prise garde le contexte des ADR et le marque remplacé. Le plan et le livrable se contredisent, et un relecteur qui rejoue le grep conclut à un échec. | Restreindre le critère, par exemple `grep -ri ... README.md aidd_docs/memory --exclude-dir=internal`, ou écrire qu'une ADR marquée remplacée est admise. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 90% (9/10)                                        |
| Files checked | app/transcribe.py, app/fake.py, app/jobs.py, app/main.py, app/runs.py, app/static/app.js, app/static/index.html, e2e/test_page.py, tests/test_fake.py, tests/test_jobs.py, tests/test_runs.py, README.md, aidd_docs/memory/api.md, aidd_docs/memory/architecture.md, aidd_docs/memory/design.md, aidd_docs/memory/project-brief.md, aidd_docs/memory/testing.md, aidd_docs/memory/internal/decisions/stack.md, aidd_docs/memory/internal/decisions/run-storage.md |
| Unchecked     | grep « sans horodatage » vide sur `aidd_docs/memory` — fixed (besoin tenu par la ligne de remplacement datée de `stack.md:6`, lettre du critère à amender) |
| Unplanned     | `tests/test_jobs.py:83-90` et `tests/test_runs.py:78-82`, tests en plus, cohérents avec le plan. `run-storage.md:27` et `stack.md:6`, mises à jour des ADR issues de la revue précédente |
