# Design

The visual language: the design system, tokens, and UI conventions. What it looks like, not how it is coded.

## System

- No design system. Styling is Tailwind utility classes written inline in `app/static/index.html`, loaded from the Play CDN.
- Two themes, light and dark, in palette B (lagoon and coral). The page follows `prefers-color-scheme`, and the button in the header forces one of them. The choice is kept in `localStorage` under `yt-transcriber-theme`.
- The `dark` class on `<html>` drives the `dark` variant (`@custom-variant`). A script in `<head>` sets it before first paint, so there is no flash.

## Tokens

- Semantic colors as CSS variables per theme, exposed to Tailwind by `@theme inline`: `canvas`, `surface`, `line` (soft fill of the icon buttons), `border` (field outlines, at least 3:1 on canvas and surface), `ink`, `muted`, `action`, `on-action`, `action-hover`, `accent`, `danger`. No `slate-*`, `sky-*` or `red-*` class in the page.
- The measured contrast ratios sit in a CSS comment above the variables. Text pairs are above 4.5, component pairs above 3, placeholders use `muted` on `surface`. The status line uses `accent`. Recompute them before changing a color.
- Spacing is the Tailwind defaults, set where it is used.

## Accessibility

- The error line has `role="alert"`, the copy icon button has an `aria-label`.
- The theme button has a stable `aria-label` ("Thème sombre") and an `aria-pressed` that is true in dark.
- The UI text is in French.
