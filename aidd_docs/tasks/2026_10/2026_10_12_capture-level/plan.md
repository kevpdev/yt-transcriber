---
objective: "L'utilisateur ou un agent choisit au lancement d'un job s'il capture aussi les images, le niveau est gardé dans le run et l'extraction se voit dans `stage`."
status: implemented
---

# Plan: Choisir le niveau de capture au lancement

## Overview

| Field      | Value                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------- |
| **Goal**   | Un champ `level` dans `POST /jobs`, une colonne dans `runs`, une étape `extracting`, une case dans la page |
| **Source** | Issue GitHub kevpdev/yt-transcriber#51                                                          |

## Phases

| #   | Phase                                                    | File                         |
| --- | -------------------------------------------------------- | ---------------------------- |
| 1   | Niveau par job côté API, run et étape `extracting`        | [`phase-1.md`](./phase-1.md) |
| 2   | Case dans la page, scénario Playwright, mémoire et README | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| `POST /jobs` accepte un champ optionnel `level`, `"text"` par défaut ou `"frames"`. Toute autre valeur donne `422` avec un `detail` en français | supposé : l'issue demande « un champ de niveau » sans le nommer. Deux valeurs fermées laissent la place à un troisième niveau sans casser le contrat |
| Le niveau est une colonne `runs.level TEXT NOT NULL DEFAULT 'text'`, schéma version 4 par `ALTER TABLE`, rendue par `GET /runs/{id}` et le résumé de `GET /runs` | une colonne se filtre en SQL, contrairement au JSON `settings` qui décrit le modèle. Le `DEFAULT` remplit les anciens runs, qui étaient tous sans images |
| Nouvelle étape `extracting` entre `transcribing` et `done`, seulement au niveau `frames`, affichée « Extraction des images » | demandée par l'issue. Sans pourcentage : `capture_frames` n'a pas de rappel de progression |
| Le drapeau global `JobStore(frames=...)` disparaît au profit de `JobStore.start(frames)` par job | il était marqué provisoire en attendant #51 (`app/jobs.py`) |
| `fake_capture` attend `FAKE_CAPTURE_DELAY` secondes (3 s), que les tests unitaires ramènent à 0 | sinon l'étape `extracting` passe entre deux interrogations de la page (2 s) et le scénario Playwright ne la voit pas |
| La case à cocher de la phase 2 est remplacée par deux boutons de soumission, « Transcrire » et « Transcrire avec les slides » | demande de l'utilisateur après la revue : le choix se fait au clic de lancement, en un clic, sans case oubliée cochée |
| Un échec de capture laisse toujours le job `done` sans images | choix de #50 reconduit, le rendre visible sort du périmètre de l'issue |
