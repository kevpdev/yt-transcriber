---
objective: "Coller une URL YouTube dans une page locale et obtenir la transcription brute, copiable en un clic, produite sur le GPU local."
status: pending
---

# Plan: MVP yt-transcriber

## Overview

| Field      | Value                                                                       |
| ---------- | --------------------------------------------------------------------------- |
| **Goal**   | Application locale FastAPI + page vanilla, transcription faster-whisper GPU |
| **Source** | `docs/adr/0001-stack.md` et la demande « Prompt 2 : implémentation du MVP » |

## Phases

| #   | Phase                                  | File                         |
| --- | -------------------------------------- | ---------------------------- |
| 1   | Backend : API, jobs, audio, Whisper    | [`phase-1.md`](./phase-1.md) |
| 2   | Front : page unique et bouton copier   | [`phase-2.md`](./phase-2.md) |
| 3   | Packaging Docker, README, git, e2e GPU | [`phase-3.md`](./phase-3.md) |

## Resources

| Source                                                       | Verified                                                                           |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `docs/adr/0001-stack.md`                                     | stack, réglages Whisper, pièges PyAV et `LD_LIBRARY_PATH`, réservation GPU Compose |
| https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4          | Play CDN Tailwind v4 cité par l'ADR                                                |

## Decisions

| Decision                                                  | Why                                                                |
| --------------------------------------------------------- | ------------------------------------------------------------------ |
| Un seul job à la fois, verrou en mémoire, pas de base     | un seul GPU, un seul utilisateur, pas d'historique (supposé)       |
| Transcription dans un thread, API non bloquée             | `GET /jobs/{id}` doit répondre pendant que Whisper tourne          |
| Texte brut sans horodatage, langue détectée, pas de select | ADR 0001, section Langue                                           |
