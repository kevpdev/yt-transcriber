# Review: thème clair et sombre (#7)

- **Verdict**: changes-requested
- **Diff**: `main...feat/light-dark-theme` (4db323f, 34ba15b)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_07
- **Findings**: 0 critical, 3 warning, 4 minor

## Phases

### Phase 1 — Thème, bouton et mémoire à jour

- [x] Un commentaire liste les ratios des deux thèmes, tous au-dessus de leur seuil — `app/static/index.html:20-26`. Les paires listées passent leur seuil au recalcul. Deux valeurs sont légèrement fausses et des paires manquent, voir Findings.
- [x] `grep -E "slate-|sky-|red-" app/static/index.html` ne renvoie rien — grep exécuté, sortie vide.
- [x] Sans choix gardé la page suit le système, après un clic le choix survit au rechargement — `app/static/index.html:7-15,104-124`, `e2e/test_page.py:106-122`. Sonde Playwright : système clair donne `dark: False`, système sombre `dark: True`, `aria-pressed` suit.
- [x] `scripts/e2e.sh fake` passe, les cinq scénarios de #5 inchangés — exécuté : `6 passed in 33.24s`, exit 0. Seule la docstring du module change (`e2e/test_page.py:1`).
- [x] `design.md` ne dit plus « Dark theme only » et nomme la palette B — `aidd_docs/memory/design.md:8`.

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | `app/static/index.html:31,44,80,92` | La bordure `--line` des champs fait 1,39 sur `canvas` en clair (1,47 sur `surface`), 1,48 en sombre (1,31 sur `surface`). `surface` contre `canvas` fait 1,06 / 1,13, donc la bordure est le seul repère du champ, sous le 3:1 de WCAG 1.4.11. L'ancien `slate-700` faisait 1,95 : régression. Le commentaire ligne 26 affirme « every component pair above 3 » sans lister `line`. | Assombrir `--line` en clair et l'éclaircir en sombre jusqu'à ≥ 3 sur `canvas` et `surface`, ou un jeton de bordure dédié aux champs, et ajouter la paire au commentaire. |
| 🟡 warning | fit | 1 | `app/static/index.html:79,91` | Le placeholder vient de la preflight du Play CDN (`color-mix(in oklab, currentcolor 50%, transparent)`, calculé `oklab(0.208 … / 0.5)` dans Chromium), soit `ink` à 50 % sur `surface` : 3,39 en clair, sous 4,5. Le commentaire ligne 26 (« Every text pair is above 4.5 ») et `design.md:14` sont donc faux. | Ajouter `placeholder:text-muted` sur `#url` et `#out` (muted sur surface : 6,33 clair, 7,31 sombre) et lister la paire dans le commentaire. |
| 🟡 warning | fit | 1 | `app/static/index.html:80,87` | L'objectif de #7 veut « une couleur d'accent pour les états (progression, succès) ». `accent` ne sert qu'à `focus:border-accent`. `#status`, qui porte la progression et « Terminé. », reste `text-muted`. Le plan n'a pas repris ce point. | Passer `#status` en `text-accent` (4,87 clair, 6,61 sombre, déjà mesurés), changement de classe seul sans toucher la logique, ou noter dans l'issue que l'accent est réduit au focus. |
| 🟢 minor | code | 1 | `app/static/index.html:21,23` | `muted 5.95` et `8.21` ne correspondent pas au mélange réellement rendu (`color(srgb 0.367 0.375 0.390)` calculé dans Chromium) : 5,98 et 8,24. | Corriger les deux nombres. |
| 🟢 minor | fit | 1 | `e2e/test_page.py:106` | Le Test Scope du plan liste le cas « localStorage lève une exception », aucun scénario ne le couvre. Vérifié à la main par sonde (`localStorage` qui lève à l'accès) : thème du système appliqué, bascule fonctionnelle, `422` affiché, `pageerrors: []`. | Ajouter un scénario avec `add_init_script` qui fait lever `localStorage`. |
| 🟢 minor | code | 1 | `app/static/index.html:69` | `aria-pressed="true"` sur un libellé « Basculer entre thème clair et sombre » ne dit pas quel état est « pressé » à un lecteur d'écran. | Libellé « Thème sombre » avec `aria-pressed`, ou garder un libellé d'action et retirer `aria-pressed`, puis aligner `design.md:20`. |
| 🟢 minor | conform | - | `aidd_docs/tasks/2026_10/2026_10_07_light-dark-theme/` | Le dossier du plan n'est pas versionné et reste `status: pending`, alors que les runs précédents commitent le leur (`git ls-files aidd_docs/tasks`). | Commiter le dossier avec le statut à jour. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (5/5) |
| Files checked | `app/static/index.html`, `e2e/test_page.py`, `aidd_docs/memory/design.md`, `aidd_docs/memory/forms.md`, `aidd_docs/memory/testing.md`, `README.md` (aucune mention de thème) |
| Unchecked     | none |
| Unplanned     | `e2e/test_page.py` (scénario de thème, sert le critère 3), `aidd_docs/memory/testing.md:28` (six scénarios, vrai). Les deux sont justifiés. |
