---
objective: "La CI de ce dépôt est capitalisée en une fiche réutilisable, un script mesure qu'un dépôt respecte le contrat, et la fiche tourne verte sur un second projet."
status: in-progress
---

# Plan: fiche de démarrage CI et contrôle de conformité

## Overview

| Field      | Value                                                                 |
| ---------- | --------------------------------------------------------------------- |
| **Goal**   | Contrat CI en trois jobs aux noms fixes, script de conformité, `codeql.yml`, ruleset scripté, appliqué à `kevpdev/swapi` |
| **Source** | issue GitHub `kevpdev/yt-transcriber#40`                              |

## Phases

| #   | Phase                                                     | File                         |
| --- | --------------------------------------------------------- | ---------------------------- |
| 1   | Dépôt yt-transcriber : noms du contrat, CodeQL, `check.sh` | [`phase-1.md`](./phase-1.md) |
| 2   | agent-config : fiche, section `aidd.md`, scripts           | [`phase-2.md`](./phase-2.md) |
| 3   | Ruleset appliqué et conformité prouvée ici                | [`phase-3.md`](./phase-3.md) |
| 4   | Application à `kevpdev/swapi`                             | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| doc GitHub Code Security, vérifiée le 2026-10-07 par l'issue | CodeQL gratuit en dépôt public, GitHub Code Security requis en privé |
| `gh api repos/kevpdev/yt-transcriber/rulesets/24662094`, 2026-10-08 | contextes requis actuels : `scan`, `check (ruff, pyright, pytest)`, `e2e (Playwright, fake transcriber)` |
| `gh api repos/kevpdev/swapi`, 2026-10-08 | public, Java 21, Spring Boot 3.3.4, `mvnw` présent, aucun `.github/`, aucun ruleset |

## Decisions

| Decision | Why |
| -------- | --- |
| Trois jobs aux noms fixes : `check`, `security`, `e2e` (conditionnel) | les noms ne dépendent plus de la stack, le ruleset est le même partout |
| `security` ne contient que Trivy. CodeQL vit dans `codeql.yml`, non requis | l'issue exclut CodeQL des checks requis tant que sa stabilité n'est pas mesurée |
| `::group::` dans `check.sh` d'abord, une étape par outil seulement si le surcoût mesuré est faible | l'issue demande de mesurer avant de choisir |
| Le ruleset se modifie avant la fusion de la phase 1, une fois les nouveaux noms rapportés sur la PR | le ruleset n'a aucun acteur de contournement, les anciens contextes bloquent la fusion et les nouveaux ont déjà rapporté |
