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

Les images sont écrites en WebP et rangées selon `run-storage.md`. Les seuils et le plafond se calibrent sur la vidéo de référence `gsxiFd8AZQU` (#53).

## Alternatives

- **Installer le binaire `ffmpeg` par `apt`** : un paquet système de plus et une seconde version de FFmpeg à suivre, à côté de celle de PyAV, sans rien apporter que PyAV ne fasse.
- **Télécharger la vidéo avec son audio** : yt-dlp devrait fusionner les flux, la seule étape où il appelle le binaire `ffmpeg`.
- **Format `h264`** : près de trois fois le poids de l'AV1 en 720p.
- **Extraire les images à chaque job** : le mode texte paierait le téléchargement vidéo pour rien.
- **Filtre de scène de `libavfilter`** (`select='gt(scene,0.3)'`) par un graphe de filtres PyAV : reste ouvert, à comparer avec la détection numpy lors du calibrage.

## Supposé, non mesuré

- Le 720p suffit et il est nécessaire pour lire le texte d'une slide.
- Une vidéo de 56 min donne 40 à 60 images WebP, quelques Mo en tout.
- Une vidéo « tête parlante » produit peu d'images stables, donc peu de candidates.
- Le filtre de scène tourne par PyAV sans binaire.

## Conséquences

- Aucune dépendance ni paquet système ajouté à l'image.
- Le mode « texte » ne change pas, il ne télécharge jamais la vidéo.
- Un job « texte + images » télécharge environ 140 Mo de plus pour 56 min (extrapolé des 38,2 Mo mesurés sur 15 min) et dure plus longtemps.
- Les seuils sont des réglages à calibrer, pas des constantes acquises.
- Si YouTube ne propose ni AV1 ni VP9 en 720p pour une vidéo, le format de repli est `bestvideo[height<=720]` (voir « Choix faits dans #50 »).

## Choix faits dans #50

Date : 2026-10-12.

- **Échec de la capture** : le job reste `done`, sans images, et l'erreur est journalisée. Perdre une transcription réussie pour une image ratée coûte plus cher que de n'avoir pas d'images. Choix supposé, reconduit par #51 qui ne l'affiche pas à l'utilisateur.
- **Format de repli** : après AV1 puis VP9, le sélecteur de yt-dlp prend `bestvideo[height<=720]`, quel que soit le codec (`h264` compris, PyAV le décode).
