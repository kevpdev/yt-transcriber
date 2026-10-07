# Design

The visual language: the design system, tokens, and UI conventions. What it looks like, not how it is coded.

## System

- No design system. Styling is Tailwind utility classes written inline in `app/static/index.html`, loaded from the Play CDN.
- Dark theme only: `slate` surfaces with a `sky` accent.
## Tokens

- None. Colors and spacing are the Tailwind defaults, set where they are used.

## Accessibility

- The error line has `role="alert"` and the copy icon button has an `aria-label`.
- The UI text is in French.
