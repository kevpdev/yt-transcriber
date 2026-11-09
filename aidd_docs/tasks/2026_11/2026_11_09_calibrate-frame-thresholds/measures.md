# Mesures du calibrage de la capture des slides (#53)

Mesuré le 2026-11-09 avec `scripts/calibrate_frames.py`, dans l'image de l'app (PyAV 18.1.0), yt-dlp de l'image, sur une RTX 5060 Ti (la capture n'utilise pas le GPU).

## Verdict

La détection numpy est gardée, avec ses seuils de changement, de stabilité et de hash inchangés (6.0, 3 s, 6 bits). Le plafond `MAX_FRAMES` passe de 80 à 200. À 80, il tronquait la vidéo de référence : la capture s'arrêtait à 47:55 sur 56 min, et les 9 dernières slides étaient perdues.

Le critère qui a fait pencher est la couverture relue à l'œil, pas le nombre d'images. Le filtre de scène coûte 2,6 fois moins (23,4 s de décodage contre 61,5 s de capture, sélection comprise, sur 56 min), mais il rate les slides construites progressivement et laisse des trous de plus de 10 min.

## Les deux vidéos

| Vidéo | Durée | Flux téléchargé | Téléchargement | Capture telle que livrée (échantillonnage + sélection) | Passe du filtre de scène |
| --- | --- | --- | --- | --- | --- |
| `KnXm3PbNz5A` | 15 min | AV1 1280x720, 38,2 Mo | 2,9 s | 19,4 s, 49 images | 6,3 s, 27 382 images notées |
| `gsxiFd8AZQU` | 56 min | AV1 1280x720, 104,7 Mo | 6,5 s | 61,5 s, 80 images (plafond atteint) | 23,4 s, 100 777 images notées |

Le banc reproduit l'app : aux seuils livrés, il retrouve les 49 images de `KnXm3PbNz5A`, comme les 6 runs `frames` de `data/runs.db`.

`KnXm3PbNz5A` alterne une caméra face au présentateur, des écrans de démo et un tableau blanc dessiné en direct. `gsxiFd8AZQU` est fait de slides à fond clair construites ligne par ligne pendant 30 min, puis d'une démo de terminal et de VS Code.

## Détection numpy, balayage

Nombre d'images retenues sans plafond, et entre parenthèses les paires d'images retenues à 10 bits de dHash ou moins. Ces paires surestiment les doublons : la relecture montre que la plupart sont des slides distinctes sur le même gabarit.

`HASH_DISTANCE` à 6 :

| `STABLE_S` \ `CHANGE_THRESHOLD` | 3 | 6 | 8 | 12 |
| --- | --- | --- | --- | --- |
| 2 s, KnXm3PbNz5A | 57 (13) | 63 (16) | 70 (23) | 81 (43) |
| 3 s, KnXm3PbNz5A | 41 (4) | **49 (7)** | 54 (8) | 65 (19) |
| 4 s, KnXm3PbNz5A | 32 (2) | 37 (2) | 40 (3) | 49 (10) |
| 2 s, gsxiFd8AZQU | 120 (110) | 94 (52) | 86 (41) | 73 (24) |
| 3 s, gsxiFd8AZQU | 107 (86) | **89 (49)** | 81 (31) | 65 (19) |
| 4 s, gsxiFd8AZQU | 99 (90) | 85 (42) | 79 (34) | 64 (23) |

Les CSV complets (7 seuils de changement, 4 durées de stabilité, 4 distances de hash) se régénèrent avec `sweep`.

### Ce que la relecture a tranché

- **`HASH_DISTANCE` de 6 à 10** ramènerait `gsxiFd8AZQU` à 70 images, sous l'ancien plafond. Mais sur les 21 images qu'il retire, 20 sont des slides distinctes, dont deux étapes plus complètes d'une slide construite ligne par ligne (01:17, 08:45) : « Mythes à dégommer » fusionnée avec « Ce que Claude Code ne fait pas », « Assistif vs agentique », « N8N remplace par Claude Code ? », « À retenir ». Le dHash sur une grille 9 x 8 ne distingue pas deux slides claires du même gabarit, souvent séparées de 30 min. Seul 19:02 contre 19:09 (le même tableau comparatif) est un vrai doublon. Sur `KnXm3PbNz5A`, 2 des 6 retraits sont des doublons (le présentateur filmé à 01:35 et 13:57, le même écran de démo à 08:09 et 08:26). Le hash reste à 6.
- **`STABLE_S` à 2 s** récupère sur `KnXm3PbNz5A` l'écran de 00:30, manqué à 3 s. Mais il ajoute surtout des rafales à 3 s d'écart pendant les défilements (4:51, 4:54, 4:57, 5:00, ou 12:58 à 13:28) et perd 4 écrans. **À 4 s**, il perd 16 écrans réels, dont « How an LLM answers » (01:16) et 05:04 à 05:18. La stabilité reste à 3 s.
- **`CHANGE_THRESHOLD`** : monter le seuil fait retenir plus d'images, parce qu'un petit mouvement (le présentateur en incrustation) ne relance plus le chrono de stabilité. Aucune valeur relue ne fait mieux que 6, qui reste.
- **Slides manquées à 6.0 / 3 s / 6**, relues sur les 5 premières minutes de `KnXm3PbNz5A` contre la planche à 5 s : les écrans qui tiennent moins de 3 s sans bouger (00:10, 00:30, 00:55, l'animation de 01:30). Un tableau de barres qui se remplit de 01:00 à 01:15 est saisi à 00:57, encore vide.

## Filtre de scène de libavfilter

`select` avec la métadonnée `lavfi.scene_score`, par `av.filter.Graph`, sans binaire `ffmpeg`. Chaque coupure au-dessus du seuil est représentée par l'échantillon pris 3 s plus tard, puis le même dédoublonnage dHash que l'app est appliqué.

| Seuil | KnXm3PbNz5A coupures / images | gsxiFd8AZQU coupures / images |
| --- | --- | --- |
| 0.1 | 208 / 87 | 173 / 92 |
| 0.2 | 111 / 59 | 80 / 60 |
| 0.3 | 60 / 34 | 54 / 46 |
| 0.4 | 52 / 29 | 45 / 41 |
| 0.5 | 34 / 22 | 37 / 36 |

Relu à 0.3 sur les deux vidéos :

- Il saisit les écrans courts que numpy manque (00:10, 00:33 et 04:53 sur `KnXm3PbNz5A`).
- Il garde 7 plans du présentateur filmé sur 34 images, à chaque changement de caméra.
- Il ne voit pas les changements sans coupure franche : une image entre 9:53 et 13:57 sur `KnXm3PbNz5A`, rien entre 30:06 et 41:00 ni entre 18:32 et 22:37 sur `gsxiFd8AZQU`.
- Il saisit une slide construite ligne par ligne à sa première ligne (« Objectif » à 00:15, « Qui est concerné ? » à 01:00), et rate la version complète.

## Plafond

- 89 images sont nécessaires pour `gsxiFd8AZQU` aux seuils gardés. Le pic de densité mesuré est de 33 images en 10 min (`KnXm3PbNz5A`, première tranche), soit environ 200 pour une heure.
- Les WebP déjà écrits pèsent 34 Ko en moyenne (633 fichiers, 21,6 Mo dans `data/frames`), donc 200 images font environ 7 Mo.
- `MAX_FRAMES` passe à 200. Supposé suffisant pour les talks visés (15 à 56 min), il n'est plus atteint par aucune des deux vidéos.
