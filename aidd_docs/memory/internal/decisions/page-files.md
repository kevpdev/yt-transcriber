# Découpage de la page en fichiers

- Date: 2026-10-07
- Status: Accepted
- Refines: `aidd_docs/memory/internal/decisions/stack.md`, ligne « Front » (une page HTML), sans la remplacer

Prépare l'issue #42.

## Contexte

`app/static/index.html` fait 251 lignes et mêle quatre rôles : le balisage, les variables de thème avec le commentaire des ratios de contraste, la logique de transcription et le bouton de thème. Chaque changement de couleur ou de logique touche le même fichier que le balisage, et le diff mélange des intentions sans rapport.

Mesure faite le 2026-10-07 sur le code de `@tailwindcss/browser@4` : le CDN ne lit que `style[type="text/tailwindcss"]`, jamais un `<link>`. La doc du Play CDN ne décrit que cette forme pour du CSS personnalisé. Les directives Tailwind (`@custom-variant`, `@theme inline`) ne peuvent donc pas quitter la page.

## Décision

La page est découpée en trois fichiers servis par FastAPI sous `/static` :

- `index.html` : le balisage, un petit `<style type="text/tailwindcss">` avec `@custom-variant` et `@theme inline`, et le script de thème du `<head>`.
- `theme.css` : les variables `:root` et `html.dark` et le commentaire des ratios, chargé par `<link rel="stylesheet">`. C'est du CSS ordinaire, `@theme inline` ne fait que le nommer.
- `app.js` : la transcription et le bouton de thème, chargé par `<script defer>`.

Le script de thème du `<head>` reste inline : il doit s'exécuter avant le premier affichage, un fichier externe bloquant ou différé ferait clignoter la page. Il déclare `THEME_KEY` et `systemDark`, que `app.js` réutilise.

Toujours pas de build front.

## Alternatives

- **Tout garder dans `index.html`** : le fichier continue de mêler quatre rôles.
- **Tailwind CLI avec un build** : permettrait un vrai `@theme` externe, mais ajoute un build et un `node_modules` pour une page, ce que `stack.md` refuse.
- **Sortir aussi `@theme inline` et `@custom-variant`** : le CDN ne lit pas ce fichier, les classes `bg-canvas` et `dark:` cesseraient de fonctionner.
- **Sortir le script de thème du `<head>`** : un flash du mauvais thème au chargement.

## Risque accepté

La page fait trois requêtes de plus au chargement (`theme.css`, `app.js`). L'outil est local, le coût est négligeable. Les variables sont chargées par `<link>` avant le script Tailwind, donc sans flash de style.

## Conséquences

- `create_app` monte `StaticFiles` sur `/static`, la route `/` ne change pas.
- Le `Dockerfile` copie déjà `app` en entier (`COPY app app`), les nouveaux fichiers sont dans l'image.
- `architecture.md`, `codebase-map.md` et `design.md` cessent de parler d'une page unique.
- Un changement de couleur ne touche plus que `theme.css`, un changement de logique que `app.js`.
