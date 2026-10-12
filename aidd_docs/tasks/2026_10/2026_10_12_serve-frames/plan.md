---
objective: "Un agent télécharge chaque image d'un run illustré à partir de l'URL relative listée dans `GET /runs/{id}`."
status: implemented
---

# Plan: Servir les images d'un run

## Overview

| Field      | Value                                                                              |
| ---------- | ---------------------------------------------------------------------------------- |
| **Goal**   | Route `GET /runs/{id}/frames/{name}` et champ `url` sur chaque image du résultat d'un run |
| **Source** | Issue GitHub kevpdev/yt-transcriber#52, ADR `internal/decisions/generation-outside-app.md` |

## Phases

| #   | Phase                                        | File                         |
| --- | -------------------------------------------- | ---------------------------- |
| 1   | Route des images, champ `url`, tests et mémoire | [`phase-1.md`](./phase-1.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Un fichier n'est servi que s'il figure dans les lignes `frames` du run, retrouvé par son nom de fichier | ferme la traversée de chemin (`../runs.db`) sans avoir à valider le nom à la main : la base fait office de liste blanche |
| `url` relative (`/runs/{id}/frames/0000.webp`) ajoutée à chaque image, `path` gardé | l'ADR fait de l'API un contrat public lu par les skills du vault, donc on ajoute un champ sans en retirer |
| L'URL est construite dans `app/main.py`, la recherche du fichier dans `RunStore` | l'URL est une affaire HTTP, le chemin sur disque une affaire de stockage |
| `404 {"detail": "Image inconnue."}` pour une image absente de la base ou du disque, `404 {"detail": "Run inconnu."}` pour un run inconnu | même format d'erreur que les autres routes, en français |
| Une base `:memory:` ne sert aucune image | elle n'a pas de dossier, `frames_dir` vaut déjà `None` |
