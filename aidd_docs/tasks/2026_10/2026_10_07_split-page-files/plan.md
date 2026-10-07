---
objective: "index.html ne contient plus ni les variables de thème ni la logique de transcription, et la page s'affiche à l'identique."
status: pending
---

# Plan: découper la page en fichiers

## Overview

| Field      | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| **Goal**   | Sortir les variables de thème et la logique de la page dans `theme.css` et `app.js` |
| **Source** | kevpdev/yt-transcriber#42                                              |

## Phases

| #   | Phase                              | File                         |
| --- | ---------------------------------- | ---------------------------- |
| 1   | ADR, fichiers statiques, découpage | [`phase-1.md`](./phase-1.md) |

## Resources

| Source                                                                   | Verified                                                                                                                  |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `@tailwindcss/browser@4` (code du CDN, lu le 2026-10-07)                  | Il ne lit que `style[type="text/tailwindcss"]`, jamais un `<link>`. Les directives `@theme` et `@custom-variant` restent donc inline |
| https://tailwindcss.com/docs/installation/play-cdn                        | Seule la forme `<style type="text/tailwindcss">` est documentée pour du CSS personnalisé                                   |

## Decisions

| Decision                                                                                       | Why                                                                                                         |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `theme.css` porte les variables (`:root`, `.dark`) et le commentaire des ratios, chargé par `<link>` | Ce sont du CSS ordinaire, le CDN n'a pas besoin de les lire. `@theme inline` ne fait que les nommer              |
| `@custom-variant` et `@theme inline` restent dans un petit `<style type="text/tailwindcss">`      | Le CDN ne lit pas un fichier externe pour ces directives                                                      |
| Le script de thème du `<head>` reste inline                                                    | Il doit s'exécuter avant le premier affichage, un fichier externe bloquant ou différé ferait clignoter la page |
