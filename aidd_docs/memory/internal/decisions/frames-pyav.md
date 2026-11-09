# Capture des images avec PyAV

- Date: 2026-10-12
- Status: Accepted

Source : `aidd_docs/tasks/2026_10/2026_10_09_summary-modes/analysis.md`, sections Q1 et Q3. Porté par #50, #51 et #53.

## Contexte

Le mode « résumé illustré » a besoin des slides d'une vidéo, chacune avec son horodatage, pour les placer à côté du texte. L'app ne télécharge aujourd'hui que l'audio (`-f bestaudio`), et `stack.md` exclut le binaire `ffmpeg`.

Mesures du 2026-10-09 dans l'image :

- Les bibliothèques FFmpeg sont déjà là, embarquées par PyAV (`libavcodec` 62.28, `libavformat`, `libavfilter`, `libswscale`, lu par `av.library_versions`). Seul le binaire `ffmpeg` manque (`which ffmpeg` vide).
- PyAV 18.1.0 décode `h264`, `vp9` et `av1`, et encode `png`, `mjpeg` et `libwebp`.
- Sur `KnXm3PbNz5A` (15 min), le flux vidéo seul en 720p pèse 38,2 Mo en AV1, 61,1 Mo en VP9 et 111,6 Mo en `h264`.

## Décision

Au niveau de capture « texte + images », choisi au lancement du job (#51), l'app télécharge le flux **vidéo seul** en 720p avec yt-dlp, à côté de l'audio. Elle préfère AV1, puis VP9. Tout le traitement passe par PyAV et numpy, sans binaire `ffmpeg`. La vidéo est jetée après extraction.

1. **Détecter les changements** : décoder environ une image par seconde, la réduire en niveaux de gris de petite taille, la comparer à la dernière image retenue par différence absolue moyenne. Une image n'est retenue qu'une fois l'écran stable quelques secondes.
2. **Dédupliquer** : un hash perceptuel (dHash) par image retenue, comparé à toutes les images déjà gardées, pour attraper le retour à une slide déjà vue.
3. **Plafonner** : un nombre maximal d'images par run.
4. **Rattacher** : chaque image est liée aux segments compris entre son horodatage et celui de l'image suivante. Le choix des images qui illustrent le document revient au LLM du skill de génération, hors de l'app.

Les images sont écrites en WebP et rangées selon `run-storage.md`. Les seuils et le plafond ont été mesurés par #53 sur `gsxiFd8AZQU` et `KnXm3PbNz5A`, voir « Calibrage (#53) ».

## Alternatives

- **Installer le binaire `ffmpeg` par `apt`** : un paquet système de plus et une seconde version de FFmpeg à suivre, à côté de celle de PyAV, sans rien apporter que PyAV ne fasse.
- **Télécharger la vidéo avec son audio** : yt-dlp devrait fusionner les flux, la seule étape où il appelle le binaire `ffmpeg`.
- **Format `h264`** : près de trois fois le poids de l'AV1 en 720p.
- **Extraire les images à chaque job** : le mode texte paierait le téléchargement vidéo pour rien.
- **Filtre de scène de `libavfilter`** (`select='gt(scene,0.3)'`) par un graphe de filtres PyAV : écarté après mesure, voir « Calibrage (#53) ». Il rate les slides construites ligne par ligne et les changements sans coupure franche.

## Supposé, non mesuré

- Le 720p suffit et il est nécessaire pour lire le texte d'une slide.
- Une vidéo « tête parlante » produit peu d'images stables, donc peu de candidates.

## Conséquences

- Aucune dépendance ni paquet système ajouté à l'image.
- Le mode « texte » ne change pas, il ne télécharge jamais la vidéo.
- Un job « texte + images » télécharge 104,7 Mo de plus pour 56 min (mesuré sur `gsxiFd8AZQU` en AV1 720p) et dure environ 80 s de plus.
- Les seuils sont des réglages mesurés sur deux vidéos, pas des constantes acquises : `scripts/calibrate_frames.py` les remesure sur une autre vidéo.
- Si YouTube ne propose ni AV1 ni VP9 en 720p pour une vidéo, le format de repli est `bestvideo[height<=720]` (voir « Choix faits dans #50 »).

## Choix faits dans #50

Date : 2026-10-12.

- **Échec de la capture** : le job reste `done`, sans images, et l'erreur est journalisée. Perdre une transcription réussie pour une image ratée coûte plus cher que de n'avoir pas d'images. Choix supposé, reconduit par #51 qui ne l'affiche pas à l'utilisateur.
- **Format de repli** : après AV1 puis VP9, le sélecteur de yt-dlp prend `bestvideo[height<=720]`, quel que soit le codec (`h264` compris, PyAV le décode).

## Calibrage (#53)

Date : 2026-11-09. Mesures complètes et relecture dans `aidd_docs/tasks/2026_11/2026_11_09_calibrate-frame-thresholds/measures.md`, banc rejouable `scripts/calibrate_frames.py`.

- **Méthode** : la détection numpy est gardée. Le filtre de scène tourne bien par PyAV sans binaire (`av.filter.Graph`, métadonnée `lavfi.scene_score`) et coûte 2,6 fois moins (23,4 s de décodage contre 61,5 s de capture, sélection comprise, sur 56 min). Mais à la relecture, il saisit les slides construites ligne par ligne à leur première ligne et laisse des trous de plus de 10 min sans coupure franche.
- **Seuils inchangés** : `CHANGE_THRESHOLD` 6.0, `STABLE_S` 3 s, `HASH_DISTANCE` 6 bits. À 10 bits, le hash retire 20 slides distinctes sur 21 : le dHash 9 x 8 ne distingue pas deux slides claires du même gabarit. À 2 s, la stabilité ajoute des rafales pendant les défilements, à 4 s elle perd des slides réelles.
- **`MAX_FRAMES` de 80 à 200** : à 80, la capture de `gsxiFd8AZQU` s'arrêtait à 47:55 sur 56 min. Ses seuils demandent 89 images, le pic mesuré est de 33 images en 10 min, et un WebP pèse 34 Ko en moyenne.
- **Mesuré** : une vidéo de 56 min donne 89 images, environ 3 Mo. Le flux AV1 720p de `gsxiFd8AZQU` pèse 104,7 Mo.
- **Limite connue** : un écran qui tient moins de 3 s sans bouger n'est pas retenu, et une animation est saisie dans son premier état stable.
