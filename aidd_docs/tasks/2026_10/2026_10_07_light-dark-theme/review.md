# Review: thème clair et sombre (#7)

- **Verdict**: changes-requested
- **Diff**: `main...feat/light-dark-theme` (4db323f..b5665dc)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_07
- **Findings**: 0 critical, 1 warning, 2 minor

## Phases

### Phase 1 — Thème, bouton et mémoire à jour

- [x] Un commentaire liste les ratios des deux thèmes, tous au-dessus de leur seuil — `app/static/index.html:19-36`. Les 24 valeurs recalculées depuis les hex (WCAG 2.x, `color-mix` en sRGB : muted `#5E6063` / `#B0B0B1`, hover `#0D708A` / `#259DBA`) concordent toutes avec le commentaire. Minimum texte 4,55 (action sur canvas clair), minimum composant 3,41 (bordure sur canvas clair). Placeholders `muted` sur `surface` 6,33 / 7,31, focus `accent` sur `surface` 5,16 / 5,87.
- [x] `grep -E "slate-|sky-|red-" app/static/index.html` ne renvoie rien — exécuté, exit 1, sortie vide.
- [x] Sans choix gardé la page suit le système, après un clic le choix survit au rechargement — `app/static/index.html:7-15,117-137`, `e2e/test_page.py:106-122`.
- [x] `scripts/e2e.sh fake` passe, les cinq scénarios de #5 inchangés — exécuté : `6 passed in 33.25s`, exit 0.
- [x] `design.md` ne dit plus « Dark theme only » et nomme la palette B — `aidd_docs/memory/design.md:8`. Les affirmations des lignes 8-20 sont vraies au code (jetons, script avant paint, placeholders, `aria-label` « Thème sombre », `aria-pressed` vrai en sombre).

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | `app/static/index.html:48-49,60-61,100` | `accent` et `danger` sont la même couleur à l'œil. Contraste entre les deux 1,25 en clair, 1,03 en sombre. En OKLCH, écart de teinte 8,5° et 8,8°, clarté 0,719 contre 0,711 en sombre. Capture Playwright, fake mode : « Terminé. » rendu `rgb(251,113,133)` juste au-dessus de l'erreur 422 rendue `rgb(248,113,113)`, indiscernables. Le succès et la progression se lisent comme une erreur, ce qui contredit l'objectif de #7 (« accent pour les états (progression, succès). L'erreur garde son rouge »). | Rendre `#status` distinct de `danger` : soit `text-action` (4,55 clair, 4,83 sombre, déjà mesurés, teinte 222°), soit un accent hors de la famille rouge (ambre ou vert), à recalculer et noter dans le commentaire. Mettre à jour `design.md:14` (« The status line uses `accent` »). Le choix de palette revient à l'utilisateur. |
| 🟢 minor | fit | 1 | `e2e/test_page.py:106` | Le cas « localStorage lève une exception » du Test Scope de `phase-1.md` n'a toujours aucun scénario (déjà relevé, non traité). | Ajouter un scénario avec `add_init_script` qui fait lever `localStorage`, vérifier thème du système et bascule sans `pageerror`. |
| 🟢 minor | rot | 1 | `app/static/index.html:11-12,120,131` | La clé `"yt-transcriber-theme"` et la requête `"(prefers-color-scheme: dark)"` sont écrites deux fois, dans le script de `<head>` et dans celui du `<body>`. | Exposer les deux depuis le script de `<head>` (par exemple sur `window`) et les réutiliser dans le second. |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (5/5) |
| Files checked | `app/static/index.html`, `e2e/test_page.py`, `aidd_docs/memory/design.md`, `aidd_docs/memory/forms.md`, `aidd_docs/memory/testing.md`, `README.md` (aucune mention de thème) |
| Unchecked     | none |
| Unplanned     | `e2e/test_page.py` (scénario de thème, sert le critère 3), `aidd_docs/memory/testing.md:28` (six scénarios, vrai). Justifiés. |
