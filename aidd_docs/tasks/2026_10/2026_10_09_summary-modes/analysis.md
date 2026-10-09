# Analyse : trois modes de sortie (texte, résumé, résumé illustré)

- Date : 2026-10-09, révisée trois fois le même jour après arbitrage de l'utilisateur
- Statut : décision proposée, à figer en ADR avant toute implémentation
- Portée : Q1 à Q6 du brief d'analyse, plus la question rouverte par l'utilisateur sur l'usage agentique. Hors périmètre : implémentation, UI détaillée, traduction (#14), file d'URLs (#12).

## Verdict

La chaîne a trois maillons, chacun avec une seule responsabilité :

| Maillon | Responsabilité | Ce qu'il ne fait pas |
|---|---|---|
| yt-transcriber | transcription horodatée, avec ou sans images, gardée run par run en SQLite avec sa télémétrie. Deux portes : la page pour l'utilisateur, l'API HTTP pour un agent | aucun LLM, aucune génération, ignore le vault |
| skill de transcription (`capture-video` réécrit) | pilote l'app et rend la transcription horodatée, plus les images si demandées | aucune note dans le vault |
| skill de génération (nouveau) | cadre la demande en posant ses questions, appelle le skill de transcription, produit un HTML ou un PDF, puis propose une note d'index dans le vault | aucune transcription |

Deux prérequis portent la chaîne. Le stockage des runs (#8) garde chaque résultat et le rend relisible par l'API. La transcription horodatée sert à l'utilisateur seule, et c'est elle qui permet de placer les images dans le document.

Légende : **mesuré** (commande lancée ce jour), **doc** (doc officielle lue ce jour), **lu** (code ou fichier lu), **supposé** (non vérifié).

## Q1. Atomique ou découpé

**Reco** : un job capture tout ce qu'il faut en une passe, au niveau choisi au lancement, « texte » ou « texte + images ». À la fin, le résultat devient un run gardé en base. La génération vient ensuite et relit ce run par l'API, le dernier ou un run choisi, sans relancer de capture.

**Critère qui a tranché** : le seul geste coûteux à refaire est le téléchargement de la vidéo. Les images doivent donc être extraites pendant le job ou jamais. Le reste se relit depuis la base autant de fois qu'il faut.

**Alternative** : tout extraire à chaque job, images comprises. Rejetée parce que le mode 1 paierait le téléchargement vidéo pour rien.

Ce qui doit exister à la fin du job, par mode :

| Donnée | Mode 1 | Mode 2 | Mode 3 | Taille par vidéo de 56 min |
|---|---|---|---|---|
| transcription horodatée, segments `start`, `end`, `text` | oui | oui | oui | quelques centaines de Ko en JSON (supposé, 14 097 mots mesurés dans l'ADR) |
| métadonnées : titre, chaîne, durée, langue | oui | oui | oui | négligeable, porté par #10 |
| images retenues, avec leur horodatage | non | non | oui | quelques Mo pour 40 à 60 images WebP 720p (supposé) |
| audio | jeté | jeté | jeté | inutile une fois transcrit |
| vidéo | non téléchargée | non téléchargée | jetée après extraction | 38,2 Mo pour 15 min en AV1 720p (**mesuré**), donc environ 140 Mo pour 56 min (extrapolé) |

Les segments horodatés existent déjà mais sont jetés : `Transcriber.run` lit `segment.end` pour la progression, puis ne garde que `segment.text` (**lu**, `app/transcribe.py`). Les garder est le prérequis. Le brief dit aujourd'hui « no timestamps », il faudra le corriger.

**Durée de vie** : chaque run est gardé, sans limite. Le job en cours reste en mémoire pour la progression, et devient un run en base à sa fin, réussi ou en erreur. Voir « Stockage des runs ».

## Stockage des runs

Question ajoutée par l'utilisateur : garder le résultat de chaque run, avec la télémétrie prévue par #8, pour qu'un skill relise le dernier run par l'API.

**Reco** : SQLite, dans un fichier sur le volume nommé de #8. Les images restent des fichiers WebP sur ce volume, la base garde leur chemin.

**Critère qui a tranché** : une base légère, sans service ni dépendance. SQLite est dans la bibliothèque standard de Python, et l'image embarque SQLite 3.46.1, qui exécute `jsonb()` et `json_extract()` (**mesuré**). Avec un seul job à la fois, il n'y a jamais d'écriture concurrente. Un run pèse quelques centaines de Ko de segments, donc 10 000 runs restent de l'ordre de quelques Go (supposé).

**Alternative** : PostgreSQL et son `jsonb`. Rejetée parce qu'elle ajoute un service au Compose pour un seul utilisateur.

| Table | Contenu | Forme |
|---|---|---|
| `runs` | une ligne par run : vidéo, état, erreur, langue, niveau de capture, temps | colonnes SQL |
| `runs`, suite | réglages du modèle, machine, versions (télémétrie de #8) | colonnes JSONB, lues en bloc |
| `segments` | `run_id`, `start`, `end`, `text` | une ligne par segment |
| `frames` | `run_id`, horodatage, chemin du fichier | une ligne par image |

- **Segments en lignes, pas en JSON** : la pagination est possible, et une recherche plein texte FTS5 sur tous les runs reste ouverte.
- **Images en fichiers** : FastAPI les sert telles quelles, la base reste petite. L'alternative, des BLOB dans SQLite, donnerait un seul fichier à sauvegarder mais une base qui grossit vite.
- **Accès** : module `sqlite3` de la bibliothèque standard, sans ORM, une écriture par run à la fin du job. Version du schéma suivie par `PRAGMA user_version`.
- **Markdown** : une vue calculée à la demande depuis les segments, jamais stockée.

API de lecture : `GET /runs`, `GET /runs/latest`, `GET /runs/{id}` (avec une vue Markdown à la demande), `GET /runs/{id}/frames/{fichier}`.

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

**Reco** : télécharger le flux **vidéo seul** en 720p avec yt-dlp, à côté de l'audio actuel, puis tout faire avec PyAV et numpy, déjà dans l'image. Pas de binaire `ffmpeg`.

**Critère qui a tranché** : FFmpeg est déjà dans l'image, sous forme des bibliothèques que PyAV embarque (`libavcodec` 62.28, `libavformat`, `libavfilter`, `libswscale`, **mesuré** par `av.library_versions`). Seul le binaire `ffmpeg` manque (**mesuré**, `which ffmpeg` vide). PyAV 18.1.0 décode `h264`, `vp9` et `av1`, et encode `png`, `mjpeg` et `libwebp` (**mesuré**). Prendre le flux vidéo seul évite la fusion audio-vidéo, qui est la seule étape où yt-dlp appelle le binaire.

**Alternative** : installer le binaire `ffmpeg` par `apt`. Rejetée parce qu'elle ajoute un paquet système et une seconde version de FFmpeg à suivre, à côté de celle de PyAV, sans rien apporter que PyAV ne fasse.

**Piste pour la détection** : `libavfilter` étant présent, le filtre de scène de FFmpeg (`select='gt(scene,0.3)'`) devrait tourner par un graphe de filtres PyAV, toujours sans binaire (supposé, non testé). À comparer avec la détection numpy lors du calibrage.

La chaîne, en quatre étapes :

1. **Obtenir** : format vidéo seul AV1 ou VP9 en 720p, 38,2 Mo à 61,1 Mo pour 15 min (**mesuré** sur `KnXm3PbNz5A`). Le 720p est supposé nécessaire pour lire le texte d'une slide.
2. **Détecter les changements** : décoder environ une image par seconde, la réduire en niveaux de gris de petite taille, et comparer à la dernière image retenue par différence absolue moyenne. Ne retenir une image qu'une fois l'écran stable quelques secondes, pour écarter transitions et animations. Seuils supposés, à calibrer sur la vidéo de référence `gsxiFd8AZQU`.
3. **Dédupliquer** : un hash perceptuel (dHash) par image retenue, comparé à **toutes** les images déjà gardées, pour attraper le retour à une slide déjà vue. Plafond dur sur le nombre d'images.
4. **Juger la pertinence** : la part déterministe rattache chaque image aux segments compris entre son horodatage et celui de l'image suivante. La part sémantique revient au LLM du skill de génération : il voit chaque image avec son texte et choisit lesquelles illustrent le document. Une vidéo « tête parlante » produit peu d'images stables, donc peu de candidates (supposé).

**Le skill `capture-video` ne couvre rien de cette chaîne** (**lu**). Il prend un transcript dont l'en-tête peut lister des chemins d'images, puis les copie dans `6 ATTACHMENTS/images/` sous une section « Captures d'écran ». Il ne télécharge, n'extrait, ni ne trie aucune image.

## Q4. Génération LLM via l'abonnement

**Reco** : la génération se fait hors de l'app, par un skill dédié du vault, dans une session que l'utilisateur lance lui-même avec l'agent de son choix. Il obtient la transcription horodatée et les images par le skill de transcription, qui appelle l'API, puis rédige le document.

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

**Reco** : l'app reste autonome et ignore le vault. `capture-video` est réécrit pour ne faire que la transcription : il pilote l'app et rend la transcription horodatée, avec ou sans images. Le skill de génération l'appelle, puis fait le reste.

**Critère qui a tranché** : une responsabilité par maillon. La note du vault n'est plus un produit de la transcription, c'est un index du document généré, donc elle revient au skill de génération.

**Alternative** : le skill de génération appelle l'app directement, sans skill de transcription. Rejetée parce que la transcription sert aussi seule, et qu'un agent doit pouvoir la demander sans passer par la génération.

Le skill de génération est interactif. Avant de produire, il pose ses questions de cadrage, avec l'outil de questions de l'agent s'il en a un, sinon en texte :

1. format : HTML ou PDF ;
2. avec ou sans images, ce qui fixe le niveau de capture demandé au skill de transcription ;
3. après production, ajouter ou non au vault une note d'index qui pointe vers le document, avec une description brève.

Articulation des issues :

- **#46** garde son objet, avec un périmètre réduit : `capture-video` transcrit par l'app, ne crée plus de note, et rend la transcription horodatée et les images. Sa dépendance à #8 (télémétrie) se réduit aux métadonnées, portées par #10.
- **#13** se ferme : le passage de la transcription au résumé est couvert par #46 et par le contrat d'API. Sa question ouverte est tranchée : le skill vient chercher.
- La réécriture de `capture-video` et le skill de génération se suivent dans le vault, pas dans ce dépôt. Où ranger le document généré dans le vault reste à trancher là-bas.

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

1. **Stockage des runs en SQLite** : remplace « Jobs live in memory only » pour les runs terminés, fixe le schéma, le volume, la rétention sans limite et les images en fichiers.
2. **Capture des images avec PyAV** : flux vidéo seul 720p, détection et dédoublonnage avec PyAV (numpy ou `libavfilter`), plafond d'images, pas de binaire `ffmpeg`.
3. **Deux portes d'usage et génération hors de l'app** : page pour l'humain, API pour l'agent, aucun LLM ni identifiant dans l'app, MCP différé.

La transcription horodatée ne demande pas d'ADR : elle ne s'écarte d'aucune décision de `stack.md`, seul le brief est à corriger.

## Issues créées

- #48 `feat(transcript): return a timestamped transcript`, après #8
- #49 `feat(api): list runs and read the latest one`
- #50 `feat(frames): download the video-only stream and extract slide frames with PyAV`
- #51 `feat(jobs): choose the capture level, text or text with frames, at submit`
- #52 `feat(api): serve the frames of a run`
- #54 `docs(api): document the agent API contract`
- #53 `test(frames): calibrate change and duplicate thresholds on the reference video`

Issues existantes : **#8** réécrite (SQLite, socle, label `next`), **#46** commentée (périmètre réduit à la transcription), **#13** fermée.

## Captures hors contrat

- Le flux vidéo seul évite la fusion, mais les formats `h264` 720p pèsent trois fois l'AV1 (111,6 Mo contre 38,2 Mo sur 15 min, **mesuré**). Le choix de format est à figer dans l'ADR des images.
- La session citée (`agent-config`, `44a79299…`) proposait une chaîne avec ffmpeg, Groq et WeasyPrint sur un VPS. Ses prémisses (VPS sans GPU, ffmpeg) ne s'appliquent pas à ce dépôt.
- Le nom `capture-video` ne dira plus ce que fait le skill réécrit. Le renommage se décide côté vault.
- Réutiliser le résultat d'une vidéo déjà transcrite devient simple avec la base (chercher un run par identifiant de vidéo), mais n'a pas encore de consommateur. À rouvrir si le même job est relancé souvent.
