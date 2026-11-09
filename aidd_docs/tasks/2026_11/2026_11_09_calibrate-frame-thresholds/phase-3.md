---
status: implemented
---

# Instruction: appliquer les seuils et consigner

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── app/
│   └── frames.py                                         ✏️
├── tests/
│   └── test_frames.py                                    ✏️  (si un test dépend d'une valeur changée)
├── README.md                                             ✏️
└── aidd_docs/memory/
    ├── codebase-map.md                                   ✏️
    └── internal/decisions/frames-pyav.md                 ✏️
```

## Test Scope

| Scenario | Action | Observable outcome | Actor |
| -------- | ------ | ------------------ | ----- |
| Setup | phase 2 a retenu la détection numpy et un jeu de seuils | `measures.md` existe | system |
| Happy path | `scripts/check.sh` | les 4 étapes passent, couverture au-dessus de 80 % | cli |
| Happy path | `docker compose run --rm --no-deps yt-transcriber python -m app.frames https://www.youtube.com/watch?v=KnXm3PbNz5A /tmp/frames` | le nombre d'images est celui que `measures.md` annonce pour ces seuils | cli |
| Edge case | `HASH_DISTANCE` change et `test_dhash_is_stable_and_tells_patterns_apart` échoue | le test est ajusté pour rester un test de comportement (deux motifs distincts restent distincts), pas pour coller à la valeur | cli |
| Teardown | `rm -r calibration` | aucun artefact de mesure dans le repo, `/tmp/frames` disparaît avec le conteneur `--rm` | cli |

## Tasks to do

### `1)` Appliquer les seuils

> Le code livré porte les valeurs mesurées.

1. Mettre à jour les constantes de `app/frames.py`.
2. Remplacer le commentaire « Provisional values » par un renvoi à la section de calibrage de l'ADR.
3. Ajuster un test de `tests/test_frames.py` seulement s'il échoue à cause d'une valeur changée.

### `2)` Consigner dans l'ADR

> L'ADR dit sur quels chiffres les seuils reposent.

1. Ajouter à `frames-pyav.md` une section « Calibrage (#53) » : vidéos, méthode retenue, seuils, tableau résumé, critère de choix, renvoi à `measures.md`.
2. Trancher les lignes « Supposé, non mesuré » que les mesures couvrent (nombre d'images pour 56 min, filtre de scène par PyAV), et retirer « Reste ouvert » de l'alternative du filtre de scène.

### `3)` Garder la mémoire et le README vrais

> Rien de ce qui est écrit ne contredit le code.

1. `codebase-map.md` : ajouter `calibrate_frames.py` à la liste de `scripts/`.
2. README, section « Capturer les slides à la main » : une ligne sur le banc et sa commande.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | `scripts/check.sh` passe, et `python -m app.frames` sur KnXm3PbNz5A donne le nombre annoncé |
| 2 | `frames-pyav.md` a sa section de calibrage, et plus de ligne supposée sur ce que les mesures ont tranché |
| 3 | `codebase-map.md` et le README citent le banc et sa commande |
