---
objective: "Un seul `scripts/check.sh` contrôle un changement du plus déterministe au plus lent (format, lint, typecheck, tests avec seuil de couverture) et s'arrête à la première étape en échec."
status: pending
---

# Plan: chaîne de contrôle déterministe

## Overview

| Field      | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| **Goal**   | `scripts/check.sh` (ruff format, ruff check, pyright, pytest) et hook pre-commit |
| **Source** | GitHub issue `kevpdev/yt-transcriber#4`                                |

## Phases

| #   | Phase                                              | File                         |
| --- | -------------------------------------------------- | ---------------------------- |
| 1   | Config, code corrigé, script, hook, mémoire projet | [`phase-1.md`](./phase-1.md) |

## Decisions

| Decision                                                        | Why                                                                                                      |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `pyright`, pas `mypy`                                           | mesuré : 3 erreurs réelles sur le code actuel, aucune due à `faster_whisper` ou `yt_dlp` (le supposé de l'issue est levé) |
| Seuil de couverture à 80 %                                      | mesuré : 82 % aujourd'hui, `audio.py` (33 %) et `transcribe.py` (48 %) touchent le vrai réseau et le GPU, hors tests par ADR |
| Config dans `pyproject.toml`                                    | un seul fichier pour `ruff`, `pyright` et `pytest-cov`, aucun outil de build déclaré                      |
| Hook versionné dans `scripts/hooks/`, activé par `core.hooksPath` | `.git/hooks` n'est pas versionné, le hook doit suivre le dépôt                                           |
