---
objective: "Deux URL envoyées à la suite sont traitées l'une après l'autre, la seconde reçoit 202 et attend en `queued` au lieu d'un 409."
status: pending
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: file d'attente des jobs

## Overview

| Field      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| **Goal**   | Remplacer le 409 « job déjà en cours » par une file FIFO traitée un job à la fois |
| **Source** | issue `kevpdev/yt-transcriber#12` et son commentaire du 2026-10-14 |

## Phases

| #   | Phase                         | File                         |
| --- | ----------------------------- | ---------------------------- |
| 1   | ADR de la file                | [`phase-1.md`](./phase-1.md) |
| 2   | File FIFO et tests            | [`phase-2.md`](./phase-2.md) |
| 3   | Mémoire et README             | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Un seul thread worker, démarré par `create_app`, qui lit une `queue.Queue` FIFO | un GPU, donc un consommateur. Un thread par job bloqué sur un verrou ne garantit pas l'ordre d'arrivée |
| L'horloge de la limite de durée (`Job.started`) repart quand le worker prend le job | attendre dans la file ne doit pas consommer les 15 minutes |
| Un job annulé pendant qu'il attend finit en `error` « Transcription annulée. », avec sa ligne `runs`, sans téléchargement | l'annulation existe déjà (#9), il suffit d'un `job.check()` au départ du worker |
| L'éviction des 20 jobs en mémoire ne retire que des jobs finis | un job en file évincé serait perdu sans trace |
| File non bornée (supposé) | un seul utilisateur, quelques URL à la fois |
| La page ne change pas (supposé) | les critères de l'issue portent sur l'API. Soumettre plusieurs URL depuis la page est une suite à ouvrir |
