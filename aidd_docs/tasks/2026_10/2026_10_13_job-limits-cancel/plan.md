---
objective: "Aucun job ne garde le GPU indéfiniment : un direct en cours est refusé, un job trop long ou annulé s'arrête et libère le verrou, et Compose n'affiche `healthy` qu'une fois le modèle chargé."
status: implemented
---

# Plan: Borner la durée d'un job, permettre l'annulation, ajouter un healthcheck

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Un job ne peut plus bloquer le service : limite de durée, annulation, refus des directs en cours, healthcheck Compose |
| **Source** | Issue GitHub kevpdev/yt-transcriber#9 |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Limite, annulation et refus des directs côté API | [`phase-1.md`](./phase-1.md) |
| 2   | Bouton « Annuler » de la page et scénario e2e | [`phase-2.md`](./phase-2.md) |
| 3   | Healthcheck Compose, mémoire et README | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| yt-dlp 2026.08.19, `yt_dlp/downloader/common.py`, `_hook_progress` (dans l'image `yt-transcriber-yt-transcriber`) | les `progress_hooks` sont appelés quel que soit `noprogress`, qui ne coupe que l'affichage |
| yt-dlp 2026.08.19, `yt_dlp/YoutubeDL.py` l.2794 | `live_status` est normalisé dans l'info (`is_live`, `is_upcoming`, `was_live`, `not_live`, `post_live`) |
| `data/runs.db`, table `runs` | le run le plus long, 1 847 s de vidéo, a pris 48 s au total (`total_s`) |

## Decisions

| Decision | Why |
| -------- | --- |
| Limite de 900 s par job, constante `JOB_TIMEOUT_S` injectable dans `create_app` (supposé) | marge d'environ 10× sur la vidéo de référence de 56 min, et les tests passent une valeur minuscule |
| Annulation coopérative : un drapeau et une échéance par job, vérifiés à des points de passage (supposé) | un thread Python ne se tue pas. Les points de passage sont le hook de progression de yt-dlp, la boucle des segments, la boucle des images et l'entre-étapes |
| Route `POST /jobs/{job_id}/cancel`, `202` demandé, `404` inconnu, `409` déjà fini (supposé) | l'arrêt n'est effectif qu'au prochain point de passage, d'où `202` et non `200` |
| Directs refusés avant le téléchargement sur `live_status` `is_live` ou `is_upcoming` (supposé) | un direct sans fin ne finirait jamais son téléchargement. Un direct terminé reste accepté |
