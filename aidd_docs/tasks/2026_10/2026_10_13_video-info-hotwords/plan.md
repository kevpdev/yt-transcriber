---
objective: "La page affiche titre, chaîne et durée de la vidéo dès que yt-dlp les connaît, télécharge le texte en `.txt` titre en tête, et envoie avec chaque job les hotwords saisis, `HOTWORDS` restant la valeur par défaut."
status: pending
---

# Plan: Infos vidéo, export `.txt` et hotwords modifiables depuis la page

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Vérifier la vidéo avant d'attendre, récupérer le texte avec son titre, régler les hotwords sans redémarrer le conteneur |
| **Source** | Issue GitHub kevpdev/yt-transcriber#10 |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Infos vidéo publiées par le job dès l'extraction des métadonnées | [`phase-1.md`](./phase-1.md) |
| 2   | Hotwords par job et route de la valeur par défaut | [`phase-2.md`](./phase-2.md) |
| 3   | Page (infos, bouton `.txt`, champ hotwords), e2e, mémoire et README | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Pas d'appel de métadonnées séparé : `download_audio` appelle déjà `extract_info(download=False)` puis `process_ie_result(download=True)` (`app/audio.py:50-55`). Un callback `on_info(title, channel, duration)` est appelé entre les deux | le point « À trancher » de l'issue est déjà résolu par le code, et un second appel réseau doublerait l'extraction |
| `GET /jobs/{id}` publie `title`, `channel`, `duration`, à `null` tant qu'inconnus (supposé) | la page lit déjà cette route toutes les 2 s, et un rechargement retrouve les infos |
| Hotwords par job : champ optionnel `hotwords` de `POST /jobs`, `null` ou vide => `HOTWORDS` ou le défaut (supposé) | aucun état serveur à garder, la valeur suit le job et la ligne `settings` du run l'enregistre |
| Route `GET /hotwords` => `{"default": "..."}` pour préremplir le champ (supposé) | la page ne connaît pas `HOTWORDS`, qui vit dans l'environnement du conteneur |
| Export `.txt` construit dans la page (Blob), sans route (supposé) | le texte et le titre sont déjà dans la page. La vue affichée est exportée, comme pour la copie |
