# Analyse : trois modes de sortie (texte, résumé, résumé illustré)

- Date : 2026-10-09
- Statut : décision proposée, à figer en ADR avant toute implémentation
- Portée : Q1 à Q6 du brief d'analyse. Hors périmètre : implémentation, UI détaillée, traduction (#14), file d'URLs (#12).

## Verdict

L'app capture, une session Claude Code lancée par l'utilisateur rédige. Le job reste atomique sur la **capture** (texte horodaté, et images si demandées au lancement), et la **génération** du résumé est une étape séparée qui relit ce que le job a gardé. Aucun LLM ne tourne dans l'app, aucun identifiant d'abonnement n'y entre.

Légende : **mesuré** (commande lancée ce jour), **doc** (doc officielle lue ce jour), **lu** (code ou fichier lu), **supposé** (non vérifié).

## Q1. Atomique ou découpé

**Reco** : le choix du niveau de capture se fait au lancement du job, avec deux niveaux, « texte » ou « texte + images ». Le résumé (modes 2 et 3) se génère ensuite, à la demande, à partir du résultat stocké. Rien n'est retéléchargé ni retranscrit.

**Critère qui a tranché** : le seul geste coûteux à refaire est le téléchargement de la vidéo, pas la transcription ni le résumé. Les images doivent donc être extraites pendant le job ou jamais. Le résumé, lui, ne dépend que de données légères.

**Alternative** : tout extraire à chaque job, images comprises. Rejetée parce que le mode 1 paierait le téléchargement vidéo et le stockage pour rien.

Ce qui doit exister à la fin du job, par mode :

| Donnée | Mode 1 | Mode 2 | Mode 3 | Taille par vidéo de 56 min |
|---|---|---|---|---|
| texte brut | oui | oui | oui | environ 100 Ko (supposé, 14 097 mots mesurés dans l'ADR) |
| segments `start`, `end`, `text` | oui | oui | oui | quelques centaines de Ko en JSON (supposé) |
| métadonnées : titre, chaîne, durée, langue | oui | oui | oui | négligeable |
| images retenues, avec leur horodatage | non | non | oui | quelques Mo pour 40 à 60 images WebP 720p (supposé) |
| audio | jeté | jeté | jeté | inutile une fois transcrit |
| vidéo | non téléchargée | non téléchargée | jetée après extraction | 38,2 Mo pour 15 min en AV1 720p (**mesuré**), donc environ 140 Mo pour 56 min (extrapolé) |
| résumé Markdown | non | ajouté plus tard | ajouté plus tard | quelques Ko |

Les segments horodatés existent déjà mais sont jetés : `Transcriber.run` lit `segment.end` pour la progression, puis ne garde que `segment.text` (**lu**, `app/transcribe.py`). Les garder ne coûte qu'un changement de type de retour.

**Durée de vie** : un dossier par job sur un volume nommé, les 20 derniers gardés, comme aujourd'hui en mémoire. Persister sur disque est nécessaire parce que la session qui rédige le résumé passe après le job, parfois après un redémarrage. C'est un écart à « Jobs live in memory only » (`architecture.md`), donc un ADR. Avec 20 jobs illustrés, le volume reste sous 200 Mo (supposé, d'après les tailles ci-dessus).

## Q2. WhisperX

**Reco** : ne pas l'adopter. Les segments de faster-whisper suffisent à aligner texte et images.

**Critère qui a tranché** : une slide reste affichée des dizaines de secondes, un segment Whisper dure quelques secondes (supposé, ordre de grandeur courant). La précision au mot de WhisperX n'apporte rien à un alignement à l'échelle de la slide. Si un jour il en faut, faster-whisper 1.2.1 expose déjà `word_timestamps` et un champ `words` sur `Segment` (**mesuré** dans l'image).

**Alternative** : WhisperX pour la diarisation. Rejetée : la diarisation passe par pyannote, qui exige un jeton Hugging Face et l'acceptation d'une licence de modèle (**doc**, README WhisperX), donc un compte, ce que le brief exclut.

Ce que WhisperX apporterait, et ce qu'il coûte :

| Apport (**doc**) | Utile ici ? |
|---|---|
| horodatage au mot par alignement wav2vec2 | non, l'échelle utile est la slide |
| diarisation pyannote | non, et elle exige un compte Hugging Face |
| inférence par lots, plus rapide | marginal : 92 s pour 56 min aujourd'hui (ADR) |

| Coût (**mesuré** sur PyPI, `whisperx` 3.8.6) | Effet sur l'image |
|---|---|
| `torch~=2.8.0`, `torchaudio`, `torchvision`, `triton`, `pyannote-audio>=4`, `transformers` | une seconde pile CUDA à côté de CTranslate2, l'image fait déjà 4,75 Go (**mesuré**) dont 2,2 Go de paquets `nvidia` |
| `faster-whisper>=1.2.0` | compatible avec la version figée |
| support de la compute capability 12.0 par `torch` 2.8 | supposé, non mesuré |

## Q3. Images (frames)

**Reco** : télécharger le flux **vidéo seul** en 720p avec yt-dlp, à côté de l'audio actuel, puis tout faire avec PyAV et numpy, déjà dans l'image. Pas de ffmpeg.

**Critère qui a tranché** : PyAV 18.1.0 de l'image décode `h264`, `vp9` et `av1`, et encode `png`, `mjpeg` et `libwebp` (**mesuré**). Prendre le flux vidéo seul évite la fusion audio-vidéo, qui est la seule étape où yt-dlp exige ffmpeg.

**Alternative** : ajouter ffmpeg et son filtre `select='gt(scene,…)'`. Rejetée parce qu'elle ajoute un binaire système pour une détection que numpy fait en quelques lignes.

La chaîne, en quatre étapes :

1. **Obtenir** : format vidéo seul AV1 ou VP9 en 720p, 38,2 Mo à 61,1 Mo pour 15 min (**mesuré** sur `KnXm3PbNz5A`). Le 720p est supposé nécessaire pour lire le texte d'une slide.
2. **Détecter les changements** : décoder environ une image par seconde, la réduire en niveaux de gris de petite taille, et comparer à la dernière image retenue par différence absolue moyenne. Ne retenir une image qu'une fois l'écran stable quelques secondes, pour écarter transitions et animations. Seuils supposés, à calibrer sur la vidéo de référence `gsxiFd8AZQU`.
3. **Dédupliquer** : un hash perceptuel (dHash) par image retenue, comparé à **toutes** les images déjà gardées, pour attraper le retour à une slide déjà vue. Plafond dur sur le nombre d'images.
4. **Juger la pertinence** : la part déterministe rattache chaque image aux segments compris entre son horodatage et celui de l'image suivante. La part sémantique revient au LLM qui rédige : il voit chaque image avec son texte et choisit lesquelles illustrent le résumé. Une vidéo « tête parlante » produit peu d'images stables, donc peu de candidates (supposé).

**Le skill `capture-video` ne couvre rien de cette chaîne** (**lu**). Il prend un transcript dont l'en-tête peut lister des chemins d'images, puis les copie dans `6 ATTACHMENTS/images/` sous une section « Captures d'écran ». Il ne télécharge, n'extrait, ni ne trie aucune image. Ce qu'il apporte, c'est la mise en note d'images déjà choisies.

## Q4. Génération LLM via l'abonnement

**Reco** : la génération se fait hors de l'app, dans une session Claude Code que l'utilisateur lance lui-même, par le skill du vault. La session lit le résultat du job par l'API (texte, segments, images), rédige le résumé, et le renvoie à l'app pour le PDF.

**Critère qui a tranché** : c'est le seul chemin qui reste dans « ordinary use of Claude Code » sans faire entrer d'identifiant d'abonnement dans l'app. La doc dit que l'authentification OAuth « *is designed to support ordinary use of Claude Code and other native Anthropic applications* », et que les développeurs de produits, Agent SDK compris, « *should use API key authentication* » (**doc**, page Legal and compliance). Claude Code 2.1.295 est installé sur l'hôte (**mesuré**), pas dans l'image.

**Alternative** : un modèle local (Ollama), si le résumé doit partir d'un bouton de la page sans session. Elle respecte le brief, mais ajoute un service et partage les 16 Go de VRAM avec Whisper, avec une qualité de résumé et de lecture d'image en français non mesurée.

| Option | Faisable ? | Écart au brief ou aux conditions |
|---|---|---|
| **session lancée par l'utilisateur, skill du vault** (reco) | oui : `claude -p` développe `/skill-name` dans le prompt et lit les images (**doc**, page headless) | aucun |
| `claude -p` dans le conteneur, avec `CLAUDE_CODE_OAUTH_TOKEN` issu de `claude setup-token` | oui techniquement : jeton d'un an prévu « *for CI pipelines and scripts* » (**doc**, page Authentication) | zone grise : un identifiant d'abonnement stocké dans l'app, et un binaire Node ajouté à l'image. Le mode `--bare`, recommandé pour les scripts, ne lit pas ce jeton (**doc**) |
| conteneur qui appelle le `claude` de l'hôte | non sans pont : le conteneur ne voit pas les binaires de l'hôte | un démon hôte à écrire et sécuriser |
| API Anthropic avec clé | oui | **écart au brief** : service payant à l'usage |
| modèle local | oui | aucun, mais qualité non mesurée |

**Le prix de la reco**, à assumer : les modes 2 et 3 ne partent pas d'un bouton de la page seul. Ils partent de la session (`/capture-video <url>`), ou la page affiche la commande à lancer pour un job déjà terminé. Le quota de l'abonnement absorbe les images envoyées au modèle (supposé, coût non mesuré).

## Q5. Skill `capture-video` ou app autonome

**Reco** : l'app reste autonome pour la capture et ignore le vault. On modifie le skill pour qu'il pilote l'app et rédige le résumé. #13 fusionne dans #46, qui s'élargit.

**Critère qui a tranché** : la question ouverte de #13, « le dépôt pousse, ou le skill vient chercher », est tranchée par Q4. Le skill vient chercher, puisque c'est lui qui porte la session LLM. #46 décrit déjà ce sens d'appel (`POST /jobs`, puis `GET /jobs/{id}`), il lui manque le résultat riche et le résumé.

**Alternative** : un nouveau skill dédié au résumé, à côté de `capture-video`. Rejetée tant que les deux font la même chose au départ, une URL YouTube vers une note.

Articulation des issues :

- **#46** s'élargit : le skill lance le job au niveau voulu, lit le résultat, rédige le résumé (structure de la note `literature` existante), place les images retenues dans `6 ATTACHMENTS/`, et renvoie le résumé à l'app pour le PDF. Sa dépendance à #8 (télémétrie) se réduit aux métadonnées, qui arrivent avec le résultat persistant.
- **#13** se ferme, avec un commentaire qui renvoie à #46.
- Le travail côté vault se suit dans le vault, pas dans ce dépôt.

## Q6. PDF

**Reco** : une page de rapport servie par FastAPI, avec une feuille de style `@media print`, et un bouton qui appelle `window.print()`. Le navigateur produit le PDF.

**Critère qui a tranché** : zéro dépendance ajoutée, et la stack reste celle de l'ADR (page HTML, JS vanilla, Tailwind via le CDN). Les images sont déjà servies par l'app.

**Alternative** : WeasyPrint 70.0 côté serveur, si le PDF doit sortir sans navigateur (par exemple déposé par le skill). Il demande les bibliothèques système Pango dans l'image (supposé, d'après la doc d'installation connue, non relue ce jour). fpdf2 2.8.9 est pur Python mais tire Pillow, absent de l'image (**mesuré**), et ne rend pas de HTML riche.

Le rendu Markdown du résumé en HTML reste à choisir à l'ADR : côté page (une bibliothèque JS par CDN, cohérent avec Tailwind) ou côté serveur (un paquet pip). Non tranché ici, choix d'implémentation.

## ADR à écrire

1. **Persistance des résultats de job sur volume** : remplace « Jobs live in memory only », fixe le contenu d'un dossier de job et la rétention.
2. **Capture des images sans ffmpeg** : flux vidéo seul 720p, détection et dédoublonnage avec PyAV et numpy, plafond d'images.
3. **Résumé délégué à la session Claude Code de l'utilisateur** : aucun LLM ni identifiant dans l'app, contrat d'API avec le skill, PDF par impression navigateur.

## Issues à créer (titres seulement)

- `feat(jobs): keep timestamped segments and video metadata in the job result`
- `feat(storage): persist job results on a named volume, keep the last 20`
- `feat(frames): download the video-only stream and extract slide frames with PyAV`
- `feat(jobs): choose the capture level, text or text with frames, at submit`
- `feat(api): expose a finished job's result, segments and frames included`
- `feat(api): accept a summary for a job and serve a printable report page`
- `test(frames): calibrate change and duplicate thresholds on the reference video`

À reprendre sur des issues existantes : élargir **#46**, fermer **#13** vers #46.

## Captures hors contrat

- Le flux vidéo seul évite la fusion, mais les formats `h264` 720p pèsent trois fois l'AV1 (111,6 Mo contre 38,2 Mo sur 15 min, **mesuré**). Le choix de format est à figer dans l'ADR 2.
- La session citée (`agent-config`, `44a79299…`) proposait une chaîne avec ffmpeg, Groq et WeasyPrint sur un VPS. Ses prémisses (VPS sans GPU, ffmpeg) ne s'appliquent pas à ce dépôt.
