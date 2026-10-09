# Analyse : trois modes de sortie (texte, résumé, résumé illustré)

- Date : 2026-10-09, révisée le même jour après arbitrage de l'utilisateur
- Statut : décision proposée, à figer en ADR avant toute implémentation
- Portée : Q1 à Q6 du brief d'analyse, plus la question rouverte par l'utilisateur sur l'usage agentique. Hors périmètre : implémentation, UI détaillée, traduction (#14), file d'URLs (#12).

## Verdict

L'app capture, les skills du vault consomment. yt-transcriber produit le texte horodaté et, si on le demande, les images d'une vidéo. Il a deux portes d'entrée : la page pour l'utilisateur, l'API HTTP pour un agent. Deux skills du vault s'appuient dessus : `capture-video`, qui en fait une note, et un nouveau skill de génération, qui en fait un document HTML ou PDF. Aucun LLM ne tourne dans l'app, aucun identifiant d'abonnement n'y entre.

Légende : **mesuré** (commande lancée ce jour), **doc** (doc officielle lue ce jour), **lu** (code ou fichier lu), **supposé** (non vérifié).

## Q1. Atomique ou découpé

**Reco** : le niveau de capture se choisit au lancement du job, « texte » ou « texte + images ». La génération est une étape séparée, faite par un skill, qui relit le résultat stocké. Une seconde demande pour la même vidéo au même niveau rend le résultat déjà calculé, sans retélécharger ni retranscrire.

**Critère qui a tranché** : le seul geste coûteux à refaire est le téléchargement de la vidéo. Les images doivent donc être extraites pendant le job ou jamais. Le reste ne dépend que de données légères, réutilisables par plusieurs consommateurs.

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

Les segments horodatés existent déjà mais sont jetés : `Transcriber.run` lit `segment.end` pour la progression, puis ne garde que `segment.text` (**lu**, `app/transcribe.py`). Les garder sert deux besoins : aligner les images sur le texte, et proposer à l'utilisateur une transcription horodatée, une fonctionnalité qu'il prévoyait sans l'avoir encore inscrite au backlog. Le brief dit aujourd'hui « no timestamps », il faudra le corriger.

**Durée de vie** : un dossier par job sur un volume nommé, les 20 derniers gardés, comme aujourd'hui en mémoire. Persister sur disque est nécessaire parce que les skills passent après le job, parfois après un redémarrage. C'est un écart à « Jobs live in memory only » (`architecture.md`), donc un ADR. Avec 20 jobs illustrés, le volume reste sous 200 Mo (supposé, d'après les tailles ci-dessus).

## Q2. WhisperX

**Reco** : ne pas l'adopter. Les segments de faster-whisper suffisent à aligner texte et images.

**Critère qui a tranché** : une slide reste affichée des dizaines de secondes, un segment Whisper dure quelques secondes (supposé, ordre de grandeur courant). La précision au mot de WhisperX n'apporte rien à un alignement à l'échelle de la slide. Si un jour il en faut, faster-whisper 1.2.1 expose déjà `word_timestamps` et un champ `words` sur `Segment` (**mesuré** dans l'image).

**Alternative** : WhisperX pour la diarisation. Rejetée : la diarisation passe par pyannote, qui exige un jeton Hugging Face et l'acceptation d'une licence de modèle (**doc**, README WhisperX), donc un compte, ce que le brief exclut.

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
4. **Juger la pertinence** : la part déterministe rattache chaque image aux segments compris entre son horodatage et celui de l'image suivante. La part sémantique revient au LLM du skill de génération : il voit chaque image avec son texte et choisit lesquelles illustrent le document. Une vidéo « tête parlante » produit peu d'images stables, donc peu de candidates (supposé).

**Le skill `capture-video` ne couvre rien de cette chaîne** (**lu**). Il prend un transcript dont l'en-tête peut lister des chemins d'images, puis les copie dans `6 ATTACHMENTS/images/` sous une section « Captures d'écran ». Il ne télécharge, n'extrait, ni ne trie aucune image.

## Q4. Génération LLM via l'abonnement

**Reco** : la génération se fait hors de l'app, par un skill dédié du vault, dans une session que l'utilisateur lance lui-même avec l'agent de son choix. Le skill lit le résultat du job par l'API (texte, segments, images) et rédige le document.

**Critère qui a tranché** : c'est le seul chemin qui reste dans « ordinary use of Claude Code » sans faire entrer d'identifiant d'abonnement dans l'app. La doc dit que l'authentification OAuth « *is designed to support ordinary use of Claude Code and other native Anthropic applications* », et que les développeurs de produits, Agent SDK compris, « *should use API key authentication* » (**doc**, page Legal and compliance). Claude Code 2.1.295 est installé sur l'hôte (**mesuré**), pas dans l'image.

**Alternative** : un modèle local (Ollama) appelé par l'app, si la génération doit partir d'un bouton de la page sans session. Elle respecte le brief, mais ajoute un service et partage les 16 Go de VRAM avec Whisper, avec une qualité non mesurée.

| Option | Faisable ? | Écart au brief ou aux conditions |
|---|---|---|
| **skill du vault dans une session lancée par l'utilisateur** (reco) | oui : `claude -p` développe `/skill-name` dans le prompt et lit les images (**doc**, page headless) | aucun |
| `claude -p` dans le conteneur, avec `CLAUDE_CODE_OAUTH_TOKEN` issu de `claude setup-token` | oui techniquement : jeton d'un an prévu « *for CI pipelines and scripts* » (**doc**, page Authentication) | zone grise : un identifiant d'abonnement stocké dans l'app, et un binaire ajouté à l'image. Le mode `--bare`, recommandé pour les scripts, ne lit pas ce jeton (**doc**) |
| conteneur qui appelle le `claude` de l'hôte | non sans pont : le conteneur ne voit pas les binaires de l'hôte | un démon hôte à écrire et sécuriser |
| API Anthropic avec clé | oui | **écart au brief** : service payant à l'usage |
| modèle local | oui | aucun, mais qualité non mesurée |

**Le prix de la reco**, à assumer : les modes 2 et 3 ne partent pas d'un bouton de la page. Ils partent d'une session d'agent. Le quota de l'abonnement absorbe les images envoyées au modèle (supposé, coût non mesuré).

## Q5. Skills du vault et autonomie de l'app

**Reco** : l'app reste autonome et ignore le vault. Deux skills consomment son API, chacun avec une seule responsabilité, et chacun appelle l'app directement :

| Consommateur | Rôle | Ce qu'il lit dans le résultat |
|---|---|---|
| `capture-video` | URL vers une note du vault, texte reformulé | texte, métadonnées |
| skill de génération (nouveau) | URL vers un document HTML ou PDF, illustré ou non | segments horodatés, images, métadonnées |

**Critère qui a tranché** : `capture-video` reformule le texte et ne garde pas les horodatages. Le skill de génération en a besoin pour placer les images, il ne peut donc pas partir de la note produite par `capture-video`. Les deux passent par l'app, qui rend le résultat déjà calculé pour une même vidéo : aucune double transcription, même si les deux skills tournent à la suite.

**Alternative** : le skill de génération appelle `/capture-video` puis travaille sur sa note. Rejetée parce que la note a perdu les horodatages et l'association texte-image.

Articulation des issues :

- **#46** garde son objet : `capture-video` transcrit lui-même par l'app au lieu d'un outil en ligne. Sa dépendance à #8 (télémétrie) se réduit aux métadonnées, qui arrivent avec le résultat persistant.
- **#13** se ferme : le passage de la transcription au skill est couvert par #46 et par le contrat d'API. Sa question ouverte, « le dépôt pousse, ou le skill vient chercher », est tranchée : le skill vient chercher.
- Le skill de génération et les changements de `capture-video` se suivent dans le vault, pas dans ce dépôt.

## Q6. Document de sortie, HTML ou PDF

**Reco** : le skill de génération produit d'abord un HTML autonome, images incluses, puis s'adapte aux outils de l'agent qui le pilote. Avec l'outil d'artefact de Claude, il publie le HTML en artefact. Sans lui, il écrit le fichier HTML en local. Le PDF se tire de ce HTML, par l'impression du navigateur ou par l'outil PDF de l'agent s'il en a un. L'app ne fait rien de cette étape.

**Critère qui a tranché** : HTML est le seul format que tous les chemins savent produire et afficher, et un PDF s'en dérive. Le skill reste agnostique de l'agent, et l'app n'ajoute aucune dépendance.

**Alternative** : générer le PDF dans l'app avec WeasyPrint 70.0, qui demande les bibliothèques système Pango dans l'image (supposé, non relu ce jour). Rejetée puisque la génération est sortie de l'app.

## Usage agentique : API HTTP ou MCP

Question rouverte par l'utilisateur après la première version : l'app doit servir aussi bien un humain qu'un agent.

**Reco** : l'API HTTP d'abord, documentée comme un contrat pour agent. Un serveur MCP viendra seulement si un agent visé n'a pas de shell pour l'appeler.

**Critère qui a tranché** : l'API existe déjà, et tout agent doté d'un shell l'appelle avec `curl`. Le skill reste ainsi agnostique sans couche de plus. Qu'aucun agent visé ne manque de shell est supposé, non vérifié.

**Alternative** : un serveur MCP monté dans l'app, qui donnerait aux agents la découverte des outils et le retour des images en contenu natif. À reprendre si le premier agent sans shell apparaît.

Conséquence sur le GPU : l'utilisateur et un agent partagent le même job unique. Le refus `409` deviendra plus fréquent, ce qui donne plus de poids à la file de #12.

## ADR à écrire

1. **Persistance des résultats de job sur volume** : remplace « Jobs live in memory only », fixe le contenu d'un dossier de job, la réutilisation par vidéo et niveau, et la rétention.
2. **Capture des images sans ffmpeg** : flux vidéo seul 720p, détection et dédoublonnage avec PyAV et numpy, plafond d'images.
3. **Deux portes d'usage et génération hors de l'app** : page pour l'humain, API pour l'agent, aucun LLM ni identifiant dans l'app, MCP différé.

## Issues à créer (titres seulement)

- `feat(jobs): keep timestamped segments and video metadata in the job result`
- `feat(ui): show the transcript with timestamps`
- `feat(storage): persist job results on a named volume, keep the last 20`
- `feat(jobs): reuse the stored result of an already-transcribed video`
- `feat(frames): download the video-only stream and extract slide frames with PyAV`
- `feat(jobs): choose the capture level, text or text with frames, at submit`
- `feat(api): expose a finished job's result, segments and frames included`
- `docs(api): document the agent API contract`
- `test(frames): calibrate change and duplicate thresholds on the reference video`

À reprendre sur des issues existantes : préciser **#46**, fermer **#13**.

## Captures hors contrat

- Le flux vidéo seul évite la fusion, mais les formats `h264` 720p pèsent trois fois l'AV1 (111,6 Mo contre 38,2 Mo sur 15 min, **mesuré**). Le choix de format est à figer dans l'ADR 2.
- La session citée (`agent-config`, `44a79299…`) proposait une chaîne avec ffmpeg, Groq et WeasyPrint sur un VPS. Ses prémisses (VPS sans GPU, ffmpeg) ne s'appliquent pas à ce dépôt.
- Le nom `capture-video` prête à confusion avec la génération. Le renommage éventuel se décide côté vault.
