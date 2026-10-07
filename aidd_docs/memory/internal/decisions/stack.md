# Stack, modèle et exposition du GPU

- Date: 2026-10-06
- Status: Accepted
- Superseded by (partiel): `aidd_docs/memory/internal/decisions/lockfile.md`, ligne « Audio » (`yt-dlp` non figé), à l'implémentation de #25

## Contexte

`yt-transcriber` est un outil local à un seul utilisateur. On colle l'URL d'une vidéo YouTube tech, en français ou en anglais, et l'outil rend la transcription brute, sans horodatage, avec un bouton copier. Le texte part ensuite vers un skill de résumé, hors de ce repo.

Les vidéos visées durent de 15 à 56 min. Aucun compte, aucun quota, aucun service payant.

La machine cible est une RTX 5060 Ti de 16 Go, en compute capability 12.0 (Blackwell), avec le driver 580 et CUDA 13.0, sous Linux Mint 22.3. Elle dispose de Docker 29.8 avec `nvidia-container-toolkit`, et de Docker Compose v5.5.1.

## Décision

| Couche | Choix | Alternative écartée, et pourquoi |
|---|---|---|
| Front | une page HTML + JS vanilla, Tailwind via le Play CDN `https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4`, servie par FastAPI | React + TS : un build et un `node_modules` pour 4 contrôles. Tailwind CLI autonome : seulement si la page doit fonctionner hors ligne |
| Back | Python 3.12 + FastAPI | Node : faster-whisper est en Python, il faudrait deux runtimes et un pont entre eux |
| Transcription | faster-whisper `1.2.1`, modèle `large-v3-turbo`, `compute_type="float16"`, appelé dans le processus de l'API, modèle chargé une fois au démarrage | `large-v3` : 3 fois plus lent, sans gain mesuré sur le vocabulaire tech. `int8_float16` : économise une VRAM dont on n'a pas besoin |
| Réglages | `language=None` (détection automatique), `beam_size=5`, `vad_filter=True`, `condition_on_previous_text=False`. `hotwords` reçoit une liste de termes tech lue dans une variable d'environnement, dont la valeur par défaut contient au moins « Claude Code, Claude, Anthropic, MCP » | sans hotwords, le modèle écrit « Cloud Code » 63 fois sur la vidéo de 56 min |
| Langue | **pas de select.** Whisper détecte la langue parlée sur les premières secondes, et le texte sort dans cette langue, sans traduction. La traduction éventuelle se fait en aval, par le skill du vault. Un petit modèle local de traduction est une étape ultérieure, hors de ce MVP | un select de langue : sans traduction, il ne ferait que forcer une langue que la détection trouve seule. Traduire dans l'app : Whisper ne traduit que vers l'anglais, et `large-v3-turbo` ne traduit pas du tout (README OpenAI : « *the `turbo` model is not trained for translation tasks* »). Il faudrait un second modèle Whisper, plus un modèle de traduction pour aller de l'anglais vers le français |
| Audio | `yt-dlp` verrouillé dans `uv.lock` puis mis à jour au build (voir `lockfile.md`), avec `deno` (paquet pip) comme runtime JS. Format `-f bestaudio`. Pas de ffmpeg, PyAV décode le `.webm` | interroger d'abord les sous-titres YouTube : les deux échantillons n'ont que des sous-titres automatiques, et ils ratent eux aussi « Claude Code » |
| Exposition du GPU | Docker, un seul service Compose, avec la réservation `deploy.resources.reservations.devices` (`driver: nvidia`, `count: all`, `capabilities: [gpu]`) | en natif : il faudrait `sudo apt install python3.12-venv`, absent de la machine |
| Image | `python:3.12-slim`, plus les paquets pip `nvidia-cublas-cu12` et `nvidia-cudnn-cu12==9.*` | `nvidia/cuda` : plus lourde, et non mesurée |
| Lancement | `docker compose up --build`, page sur `localhost:8000`, volume nommé pour `HF_HOME` (le modèle pèse 1,6 Go, téléchargé au premier démarrage) | `docker build` puis `docker run --gpus all …` : deux commandes |
| Attente côté UI | `POST /jobs` renvoie un identifiant tout de suite. La page interroge `GET /jobs/{id}` toutes les 2 s, qui renvoie l'étape (téléchargement, transcription), le pourcentage (`segment.end / info.duration`) et le texte final. Un seul job à la fois, puisqu'il n'y a qu'un GPU. Un second job reçoit un message clair | une requête synchrone qui dure plusieurs minutes, exposée aux timeouts |

## Pièges mesurés, à respecter

- **PyAV reste en `>=15,<16`.** PyAV 19.0.1 casse faster-whisper 1.2.1 avec l'erreur `open() got an unexpected keyword argument 'metadata_errors'`. PyAV 15.1.0 fonctionne.
- **`LD_LIBRARY_PATH` se calcule par `list(nvidia.cublas.lib.__path__)[0]`**, et de même pour `nvidia.cudnn.lib`. Ces paquets sont des namespaces, donc leur `__file__` vaut `None`.
- **yt-dlp a besoin de `deno`.** Sans lui, il avertit que YouTube masque des formats. Le yt-dlp du système (2024.04.09) n'est pas utilisable.

## Mesures

Conteneur `python:3.12-slim` avec GPU, deux vidéos en français : `KnXm3PbNz5A` (15 min) et `gsxiFd8AZQU` (56 min).

| Configuration | 15 min | 56 min | Pic de VRAM, au-dessus du bureau |
|---|---|---|---|
| `large-v3-turbo` fp16 | 30 s | 92 s | 2,3 à 2,7 Go |
| `large-v3-turbo` fp16 + hotwords | non mesuré | 89 s | non relevé |
| `large-v3` fp16 | 76 s | 293 s | 4,4 à 4,5 Go |
| `large-v3` int8_float16 | 66 s | 271 s | 2,4 à 2,8 Go |

- Le téléchargement de l'audio prend 2 s pour 15 min et 6 s pour 56 min.
- La VRAM ne croît pas avec la durée de la vidéo.
- CTranslate2 4.8.2 accepte `float16`, `bfloat16` et les variantes `int8` sur la compute capability 12.0.
- Avec les hotwords, « Claude Code » sort 90 fois et « Cloud Code » 1 fois sur la vidéo de 56 min.
- Le `nvidia-smi` de l'hôte affiche le processus `python` du conteneur, avec sa VRAM.
- La détection automatique de langue (`large-v3-turbo`, `vad_filter=True`) trouve `fr` avec une probabilité de 0,999 sur les deux vidéos.

## Supposé, non mesuré

- La qualité en anglais : aucun échantillon anglais n'a été mesuré, ni la détection de l'anglais.
- La qualité globale du texte : seuls les comptes de termes tech ont été comparés.
- Les hotwords retirent 0,8 % des mots (14 097 contre 14 216). On ne sait pas si ce sont des répétitions supprimées ou des pertes réelles.

## Conséquences

- Un seul runtime, Python, et une seule commande de lancement.
- Pas de build front.
- L'outil dépend d'internet pour joindre YouTube et le CDN Tailwind.
- yt-dlp verrouillé puis mis à jour au build (voir `lockfile.md`) : une reconstruction de l'image (`docker compose build --no-cache`) suffit à suivre les changements de YouTube.
