# Review: Capture des slides avec PyAV (#50)

- **Verdict**: changes-requested
- **Diff**: `main...feat/slide-frames` (4f7b847, c8e2122, cc998a0)
- **Axes run**: code, functional, relevancy (architecture conformance included)
- **Date**: 2026_10_12
- **Findings**: 0 critical, 4 warning, 7 minor

## Phases

### Phase 1 — Module de capture : téléchargement, détection, dédoublonnage

- [x] `numpy` en dépendance directe, version verrouillée inchangée — `pyproject.toml:12`, `uv.lock` diff sans ligne `version`
- [x] vidéo indisponible => `AudioError` au message français — `app/frames.py:64-65`, `tests/test_frames.py:86-105`
- [x] trois slides stables => trois images, retour à une slide vue et flash n'en ajoutent pas — `tests/test_frames.py:38-52` (sur bruit aléatoire seulement, voir Findings)
- [x] jamais plus de `MAX_FRAMES` — `app/frames.py:123-124`, `tests/test_frames.py:67-70`
- [x] `work_dir` sans vidéo après `capture_frames`, même si la sélection lève — `app/frames.py:152-154`, `tests/test_frames.py:126-142`
- [x] `scripts/check.sh` passe, couverture ≥ 80 % — relancé par le reviewer : `86 passed`, `Total coverage: 91.54%`, `EXIT=0`

### Phase 2 — Brancher la capture dans le job et la table `frames`

- [x] base v2 => v3 sans perte de runs ni de segments — `app/runs.py:133-134`, `tests/test_runs.py:79-96`
- [x] `GET /runs/{id}` rend `frames`, vide sans images — `app/runs.py:209-217`, `tests/test_runs.py:122-128`
- [x] `POST /jobs` inchangé, sans capture — `app/jobs.py:45`, `tests/test_jobs.py:141-151`
- [x] une ligne `frames` par fichier WebP présent — `tests/test_jobs.py:128-138`
- [x] capture qui lève => job `done` avec texte, aucune ligne `frames`, dossier partiel supprimé — `app/main.py:55-62`, `tests/test_jobs.py:154-169`
- [x] `scripts/check.sh` passe — idem phase 1

### Phase 3 — Preuve sur `KnXm3PbNz5A` et mémoire à jour

- [x] au moins une image horodatée, aucune vidéo restante — rejoué par le reviewer avec le code de la branche monté dans l'image : `50 frames in 23.9s, files left in work dir: []`, 57.0 s à 905.0 s, `av01.0.05M.08`, 1,7 Mo. Le chemin job réel (lignes `frames` d'un vrai run) n'est prouvé que par `fake_capture`, aucun interrupteur n'existe avant #51
- [x] `Dockerfile` sans `apt` — `grep -n apt Dockerfile` code retour 1
- [x] `architecture.md` et `integration.md` décrivent la capture, aucune ligne « audio seulement » sans nuance — grep sur `README.md` et `aidd_docs/memory/*.md`, seule `integration.md:8` qui nuance

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | fit | 1 | `app/frames.py:115,122` | L'image gardée est `start_rgb`, le premier échantillon qui franchit le seuil, souvent pris en pleine transition. Mesuré sur slides synthétiques : fondu A vers X, échantillon à 60 % du fondu, MAD mid/X 5,59 < 6 => X n'est jamais gardée, résultat `[(0, 'A')]`. Révélation de puces : MAD 2->4 lignes 5,75 => seule la version à 2 puces est gardée. Sur la vraie vidéo, l'image 0022 est un zoom en cours ("r l'IA." coupé) | garder l'horodatage `start` mais remplacer l'image par le dernier échantillon de l'écran (mis à jour tant que l'écran ne change pas) ou au moins celui du moment du commit, et hasher cette image-là. Ajouter un test fondu et un test révélation progressive |
| 🟡 warning | code | 1 | `tests/test_frames.py:24-26` | Toutes les slides de test sont du bruit aléatoire (distance dHash ~32 bits). Aucun test ne ressemble à une slide (fond uni, texte, même gabarit), donc les tests ne peuvent pas attraper le cas ci-dessus ni le suivant | ajouter des slides synthétiques à gabarit commun (fond clair, titre, lignes de texte) pour la détection et le dédoublonnage |
| 🟡 warning | rot | 3 | `aidd_docs/memory/architecture.md:31` | « A capture failure is logged and leaves the job done without images (supposed choice, see `internal/decisions/frames-pyav.md`) » : l'ADR ne parle pas de l'échec de capture, `grep -n -i "échec\|failure\|fail" frames-pyav.md` ne rend rien. La source réelle est la table Decisions de `plan.md` | citer `aidd_docs/tasks/2026_10/2026_10_12_slide-frames/plan.md`, ou ajouter la décision à l'ADR et la citer |
| 🟡 warning | rot | 3 | `aidd_docs/memory/internal/decisions/frames-pyav.md:50` | « Si YouTube ne propose ni AV1 ni VP9 en 720p, le repli reste à définir dans #50 » reste écrit alors que #50 l'a tranché (`bestvideo[height<=720]`, `app/frames.py:34`). La mémoire dit faux | ajouter une ligne datée à l'ADR : repli sur le meilleur flux vidéo seul ≤ 720p, tranché par #50 |
| 🟢 minor | code | 1 | `app/frames.py:108,116` | `start = 0.0` et la garde `start_rgb is None` sont morts : la première itération fixe toujours `start_rgb` | retirer l'initialisation et la garde |
| 🟢 minor | rot | 1 | `app/frames.py:19,65` | une erreur vidéo est une `AudioError`, et `_readable` privé d'`audio.py` est importé ailleurs | renommer en `DownloadError` métier (ou alias), rendre le formateur public |
| 🟢 minor | code | 2 | `app/runs.py:146,173` | `_relative` lève `ValueError` pour un chemin hors du dossier de la base, dans la transaction : tout le run (texte, segments) serait perdu pour une image, l'inverse du choix « une image ratée ne coûte pas le texte » | rendre le chemin relatif avant la transaction, ou ignorer les images hors racine avec un log |
| 🟢 minor | code | 2 | `app/main.py:80,90-118` | une capture réussie suivie d'un échec de `runs.record` laisse `data/frames/<run_id>/` sans aucune ligne | supprimer `frames_dir / job.id` dans l'`except` de l'enregistrement |
| 🟢 minor | rot | 3 | `aidd_docs/memory/architecture.md:15-23` | le diagramme « How it fits together » ne montre pas la capture vidéo, et `codebase-map.md` omet l'arête `runs.py -> frames.py` (`app/runs.py:9`) | ajouter le nœud capture après whisper, et l'arête runs vers frames |
| 🟢 minor | rot | 3 | `aidd_docs/memory/architecture.md:31`, `README.md:38` | le plafond 80 est recopié de `MAX_FRAMES`, que #53 va recalibrer | renvoyer à la constante plutôt que recopier la valeur |
| 🟢 minor | conform | 2 | `app/runs.py:9` | `runs.py` importe `app.frames`, donc `av` et `numpy`, pour un dataclass de trois champs | déplacer `Frame` dans un module sans dépendance lourde, ou typer par protocole |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (15/15) |
| Files checked | app/frames.py, app/main.py, app/runs.py, app/jobs.py, app/fake.py, app/audio.py, pyproject.toml, uv.lock, tests/test_frames.py, tests/test_jobs.py, tests/test_runs.py, README.md, aidd_docs/memory/{api,architecture,codebase-map,deployment,integration,testing}.md, ADR frames-pyav.md, run-storage.md |
| Unchecked     | none |
| Unplanned     | none |
