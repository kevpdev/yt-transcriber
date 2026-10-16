---
objective: "GET /runs/{id} rend la description de la vidéo telle que YouTube l'affiche, et un run écrit avant la migration se relit avec une description null."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: description de la vidéo dans le run

## Overview

| Field      | Value                                                                 |
| ---------- | --------------------------------------------------------------------- |
| **Goal**   | Stocker et rendre la description YouTube de chaque run, pour que le skill de génération y retrouve les sources |
| **Source** | Issue kevpdev/yt-transcriber#72                                       |

## Phases

| #   | Phase                                   | File                         |
| --- | --------------------------------------- | ---------------------------- |
| 1   | description du téléchargement jusqu'au run | [`phase-1.md`](./phase-1.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| La description passe par `Download`, pas par `on_info` ni par le `Job` | L'issue exclut la vue du job. Garder la signature de `on_info` laisse intacts ses appelants (`app/main.py`, `app/fake.py`, tests) |
| Schéma version 5 : `ALTER TABLE runs ADD COLUMN description TEXT`, nullable sans défaut | Même forme que l'étape 4 (`level`). Un run ancien se relit avec `null`, aucune donnée réécrite |
| La description reste hors de `GET /runs` (`RunSummary`) | Elle peut faire plusieurs milliers de caractères, la liste reste légère. Seul `GET /runs/{id}` la rend |
