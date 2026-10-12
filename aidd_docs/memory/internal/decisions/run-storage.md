# Stockage des runs en SQLite

- Date: 2026-10-12
- Status: Accepted
- Supersedes: `aidd_docs/memory/architecture.md`, ligne « Jobs live in memory only », pour les runs terminés, une fois #8 livrée

Source : `aidd_docs/tasks/2026_10/2026_10_09_summary-modes/analysis.md`, section « Stockage des runs ». Porté par #8, puis #48, #49, #50 et #52.

## Contexte

Les jobs vivent en mémoire, l'app garde les 20 derniers et un redémarrage les perd. Trois besoins demandent de garder chaque run :

- **La télémétrie de #8** : comparer les runs entre eux. L'ADR `stack.md` ne dit rien de la qualité en anglais ni de la variation d'un run à l'autre, et « Cloud Code » sort une fois dans ses mesures puis zéro fois dans le run du README, sur la même vidéo.
- **La relecture par un agent** : le skill de génération relit le dernier run, ou un run choisi, sans relancer de capture.
- **Les images** : on ne peut les extraire que pendant le job, parce que le téléchargement de la vidéo est le seul geste coûteux à refaire (voir `frames-pyav.md`).

Avec un seul job à la fois, il n'y a jamais d'écriture concurrente. L'outil sert un seul utilisateur.

## Décision

Chaque run terminé, réussi ou en erreur, est écrit dans une base SQLite, un fichier sur un volume Docker nommé. Les images restent des fichiers WebP sur ce volume, et la base garde leur chemin. Le job en cours reste en mémoire pour la progression.

| Table | Contenu | Forme |
|---|---|---|
| `runs` | une ligne par run : vidéo, état, erreur, langue, niveau de capture, temps | colonnes SQL |
| `runs`, suite | réglages du modèle, machine, versions (télémétrie de #8) | colonnes JSONB, lues en bloc |
| `segments` | `run_id`, `start`, `end`, `text` | une ligne par segment |
| `frames` | `run_id`, horodatage, chemin du fichier | une ligne par image |

- **Accès** : module `sqlite3` de la bibliothèque standard, sans ORM, une écriture par run en fin de job.
- **Schéma** : sa version est suivie par `PRAGMA user_version`.
- **Rétention** : sans limite.
- **Segments en lignes** : la pagination est possible, et une recherche plein texte FTS5 sur tous les runs reste ouverte.
- **Markdown** : une vue calculée à la demande depuis les segments, jamais stockée.
- **Lecture** : `GET /runs`, `GET /runs/latest`, `GET /runs/{id}`, `GET /runs/{id}/frames/{fichier}` (#49, #52).

SQLite 3.46.1 est dans l'image et exécute `jsonb()` et `json_extract()`, mesuré le 2026-10-09.

## Alternatives

- **PostgreSQL et son `jsonb`** : ajoute un service au Compose pour un seul utilisateur.
- **Images en BLOB dans SQLite** : un seul fichier à sauvegarder, mais une base qui grossit vite, et FastAPI ne peut plus servir les images telles quelles.
- **Segments en un champ JSON par run** : plus simple à écrire, mais ni pagination ni recherche plein texte.
- **Garder la mémoire seule** : la télémétrie et la relecture par un agent disparaissent au redémarrage.

## Supposé, non mesuré

- Un run pèse quelques centaines de Ko de segments, donc 10 000 runs restent de l'ordre de quelques Go.

## Conséquences

- L'historique survit à `docker compose down` puis `up`.
- Un agent relit un run passé par l'API, sans GPU et sans téléchargement.
- Le volume grossit sans limite. Une purge sera à décider si la taille gêne.
- Chaque évolution du schéma demande une migration, repérée par `PRAGMA user_version`.
- Retrouver un run par identifiant de vidéo devient possible, sans consommateur pour l'instant.
