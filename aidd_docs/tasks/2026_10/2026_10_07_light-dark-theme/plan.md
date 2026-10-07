---
objective: "La page suit le thème du système, un bouton force clair ou sombre avec le choix gardé après rechargement, en palette B mesurée."
status: pending
---

# Plan: thème clair et sombre

## Overview

| Field      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| **Goal**   | Remplacer le tout bleu par la palette B (lagon et corail) en deux thèmes |
| **Source** | kevpdev/yt-transcriber#7                                     |

## Phases

| #   | Phase                         | File                         |
| --- | ----------------------------- | ---------------------------- |
| 1   | Thème, bouton et mémoire à jour | [`phase-1.md`](./phase-1.md) |

## Resources

| Source                                       | Verified                                                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| https://tailwindcss.com/docs/dark-mode       | `@custom-variant dark (&:where(.dark, .dark *));` pilote la variante `dark` par une classe sur `<html>`   |

## Decisions

| Decision                                                                                      | Why                                                                                              |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Palette B, valeurs ajustées après mesure (voir phase 1), pas les valeurs de départ de l'issue | Les départs échouent : action 3,68 avec texte blanc, accent 2,54 sur fond clair, erreur 2,75 sur fond sombre |
| Des variables CSS par thème, exposées à Tailwind par `@theme inline`                          | Les classes d'utilité ne portent plus de couleur en dur, donc plus de `dark:` à répéter           |
| Le statut (progression, succès) prend la couleur d'action, l'accent corail ne colore que le focus du champ URL | L'accent corail et le rouge d'erreur ne se distinguent pas (contraste 1,25 en clair, 1,03 en sombre), un succès se lisait comme une erreur. Décidé par l'utilisateur après la revue, ce qui s'écarte de l'issue #7 sur l'usage de l'accent |
