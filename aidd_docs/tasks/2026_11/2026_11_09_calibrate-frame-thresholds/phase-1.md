---
status: implemented
---

# Instruction: banc de calibrage rejouable

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/
│   └── calibrate_frames.py   ✅
└── .gitignore                ✏️  (cache du banc)
```

## Test Scope

| Scenario | Action | Observable outcome | Actor |
| -------- | ------ | ------------------ | ----- |
| Setup | `docker compose build`, puis définir `CAL="docker compose run --rm --no-deps --user $(id -u):$(id -g) -e HOME=/tmp -e PYTHONPATH=/srv -v ./scripts:/srv/scripts -v ./calibration:/srv/calibration yt-transcriber python scripts/calibrate_frames.py"`. Toutes les commandes du banc passent par `$CAL` | le conteneur tourne avec l'utilisateur de l'hôte, `import app.frames` se résout depuis `/srv`, les sorties arrivent dans `./calibration` côté hôte | cli |
| Happy path | `$CAL sample KnXm3PbNz5A` | le cache `calibration/KnXm3PbNz5A.npz` existe, avec pour chaque image décodée son score de scène, et la vidéo téléchargée est supprimée | cli |
| Happy path | `$CAL sweep KnXm3PbNz5A` avec la grille par défaut | un CSV `calibration/KnXm3PbNz5A-sweep.csv`, une ligne par jeu de seuils : nombre d'images, paires restantes sous un dHash de 10 bits, temps de sélection | cli |
| Happy path | la ligne du CSV aux seuils actuels (6.0, 3.0, 6, 80) | 49 images, comme les 6 runs `frames` de `data/runs.db` | cli |
| Happy path | `$CAL scene KnXm3PbNz5A` | un CSV par seuil de scène (0.1 à 0.5) avec le nombre d'images, calculé sur les scores en cache, sans binaire `ffmpeg` | cli |
| Happy path | `$CAL sheet KnXm3PbNz5A --every 5` et `--params 6,3,6` | une planche contact PNG de référence et une planche des images retenues, chaque vignette légendée de son horodatage | cli |
| Edge case | `sample` alors que `av.filter.Graph` ne sait pas monter `select` | message d'erreur explicite, le cache s'écrit sans scores de scène, et la ligne « Le filtre de scène tourne par PyAV sans binaire » de l'ADR devient « mesuré : non » | cli |
| Teardown | `rm -r calibration` | sans sudo, puisque les fichiers appartiennent à l'utilisateur de l'hôte. Aucun fichier du banc ne reste dans le repo, `git status` propre | cli |

## Tasks to do

### `1)` Échantillonner une fois et mettre en cache

> Décoder chaque vidéo une seule fois, avec la même fonction que l'app.

1. Télécharger par `app.frames.download_video`, échantillonner par `app.frames.sample_frames`.
2. Garder par échantillon l'horodatage, la miniature `THUMB`, le dHash et une image réduite à 320 px de large pour les planches.
3. Dans une seconde passe sur le même fichier, avant de le supprimer, faire passer chaque image décodée dans le graphe de scène (tâche 3) et garder son score.
4. Écrire le tout dans `calibration/<video_id>.npz`, supprimer la vidéo, noter séparément le temps de chaque passe de décodage. Ce sont ces deux temps qui comparent le coût des deux méthodes, la sélection elle-même étant négligeable devant le décodage.

### `2)` Balayer les seuils de la détection numpy

> Rejouer `app.frames.select_frames` sur le cache pour chaque jeu de seuils.

1. Surcharger `CHANGE_THRESHOLD`, `STABLE_S`, `HASH_DISTANCE` et `MAX_FRAMES` du module le temps d'un appel, sur une grille par défaut (`CHANGE_THRESHOLD` 3 à 12, `STABLE_S` 2 à 5, `HASH_DISTANCE` 4 à 10, `MAX_FRAMES` levé à 1000 pour voir le nombre réel).
2. Écrire un CSV : seuils, nombre d'images, paires de doublons probables restantes, temps.

### `3)` Mesurer le filtre de scène de libavfilter

> Savoir si `select='gt(scene,X)'` tourne par PyAV et ce qu'il retient.

1. Monter un `av.filter.Graph` `buffer` puis `select` puis `buffersink`, et lire le score `scene` de chaque image dans la passe de la tâche 1.
2. Pour chaque seuil de 0.1 à 0.5, compter sur les scores en cache les images retenues, puis appliquer le même dédoublonnage dHash que l'app, dans un CSV au même format.

### `4)` Produire les planches contact

> Rendre la relecture à l'œil possible en quelques minutes.

1. Planche de référence : une vignette toutes les N secondes, légendée `mm:ss`.
2. Planche d'un jeu de seuils : les images retenues, légendées `mm:ss`.

### `5)` Garder le cache hors du repo

> Aucun artefact de mesure n'est commité.

1. Ajouter `calibration/` à `.gitignore`.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `calibration/KnXm3PbNz5A.npz` existe avec ses scores de scène, appartient à l'utilisateur de l'hôte, et le dossier de travail ne contient plus de vidéo |
| 2 | la ligne aux seuils actuels donne 49 images sur KnXm3PbNz5A |
| 3 | le CSV de scène existe, ou l'échec de `av.filter.Graph` est rapporté avec son message |
| 4 | les deux planches s'ouvrent et chaque vignette porte son horodatage |
| 5 | `git status` ne montre pas `calibration/` |
