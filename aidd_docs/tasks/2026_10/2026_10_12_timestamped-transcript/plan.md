---
objective: "Un job terminé rend ses segments horodatés par l'API et dans la table `segments`, et la page bascule entre texte brut et texte horodaté, la copie suivant la vue affichée."
status: reviewed
---

# Plan: Transcription horodatée

## Overview

| Field      | Value                                                                                              |
| ---------- | -------------------------------------------------------------------------------------------------- |
| **Goal**   | Garder les segments de Whisper au lieu de les jeter, les stocker, les exposer et les afficher       |
| **Source** | Issue GitHub kevpdev/yt-transcriber#48, ADR `aidd_docs/memory/internal/decisions/run-storage.md`    |

## Phases

| #   | Phase                                                        | File                         |
| --- | ------------------------------------------------------------ | ---------------------------- |
| 1   | Segments dans le transcripteur, le job, l'API et la base      | [`phase-1.md`](./phase-1.md) |
| 2   | Bascule de la page, scénario Playwright et mémoire à jour     | [`phase-2.md`](./phase-2.md) |

## Resources

| Source                                            | Verified                                                                                              |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| SQLite 3.45.1 de l'hôte, 2026-10-12               | `end` s'accepte comme nom de colonne sans guillemets en `CREATE`, `INSERT` et `SELECT`, donc les noms de l'ADR tiennent |
| `app/transcribe.py`, `Transcriber.run`            | les segments de faster-whisper portent déjà `start`, `end` et `text`, la boucle lit `end` pour la progression |

## Decisions

| Decision                                                                                                      | Why                                                                                                   |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Schéma en version 2, migration incrémentale : `user_version < 1` crée `runs`, `< 2` crée `segments`          | `data/runs.db` existe déjà en version 1 chez l'utilisateur, recréer la base perdrait l'historique       |
| Table `segments (run_id, position, start, end, text)`, clé `(run_id, position)`                              | l'ADR fixe `run_id, start, end, text`, `position` garantit l'ordre sans dépendre de `rowid`             |
| `runs` et `segments` écrits dans la même transaction                                                          | un lecteur qui voit le run voit ses segments, ou rien                                                  |
| Le texte horodaté est calculé dans la page depuis `segments`, une ligne par segment `[mm:ss] texte`          | l'ADR dit que les vues sont calculées à la demande, jamais stockées. `text` reste inchangé              |
| `[h:mm:ss]` décidé par segment, dès que son début atteint une heure                                           | une vidéo de moins d'une heure garde le format court partout                                           |
