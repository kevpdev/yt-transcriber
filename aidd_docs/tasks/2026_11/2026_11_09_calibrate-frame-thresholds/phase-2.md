---
status: implemented
---

# Instruction: mesures et relecture à l'œil

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
└── aidd_docs/tasks/2026_11/2026_11_09_calibrate-frame-thresholds/
    └── measures.md   ✅
```

## Test Scope

| Scenario | Action | Observable outcome | Actor |
| -------- | ------ | ------------------ | ----- |
| Setup | `$CAL sample` sur gsxiFd8AZQU et KnXm3PbNz5A, avec `$CAL` défini en phase 1 | deux caches `.npz` | cli |
| Happy path | `$CAL sweep` et `$CAL scene` sur les deux vidéos | quatre CSV | cli |
| Happy path | planches de référence et planches des 2 ou 3 meilleurs jeux de chaque méthode, relues à l'œil | pour chaque jeu : slides manquées et doublons restants, comptés avec leur horodatage | system |
| Edge case | gsxiFd8AZQU ne propose ni AV1 ni VP9 en 720p | le format de repli `bestvideo[height<=720]` est utilisé, son codec et son poids sont notés | cli |
| Edge case | le filtre de scène sort meilleur que la détection numpy sur les deux vidéos | le plan s'arrête ici, les chiffres vont dans `measures.md`, une issue de remplacement est proposée | system |

## Tasks to do

### `1)` Mesurer les deux vidéos

> Avoir les chiffres des deux méthodes sur les deux vidéos.

1. Lancer `sample`, `sweep` et `scene` sur gsxiFd8AZQU puis KnXm3PbNz5A.
2. Noter le poids et le codec du flux téléchargé, et le temps de décodage.

### `2)` Relire à l'œil

> Compter les slides manquées et les doublons, pas seulement le nombre d'images.

1. Produire la planche de référence à 5 s de chaque vidéo.
2. Retenir les 2 ou 3 jeux de chaque méthode dont le nombre d'images est le plus proche du nombre de slides lues sur la planche de référence.
3. Pour chacun, comparer sa planche à la référence et lister slides manquées et doublons avec leur horodatage.

### `3)` Choisir sur les chiffres

> Une méthode et un jeu de seuils, justifiés par le tableau.

1. Écrire `measures.md` : tableau par vidéo et par jeu (images, manquées, doublons, temps), méthode et seuils retenus, critère qui a fait pencher.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | les deux méthodes ont un CSV sur chacune des deux vidéos |
| 2 | chaque jeu relu a son nombre de slides manquées et de doublons, horodatages à l'appui |
| 3 | `measures.md` nomme la méthode et les seuils retenus, et la ligne du tableau qui les justifie |
