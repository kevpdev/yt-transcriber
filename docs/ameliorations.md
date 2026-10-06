# Améliorations prévues

Backlog des évolutions après le MVP (PR #1). Une entrée par sujet, dans l'ordre où on compte les traiter. Les choix de stack restent ceux de [`adr/0001-stack.md`](adr/0001-stack.md), toute entrée qui s'en écarte demande un nouvel ADR.

## Demandées

### 1. Télémétrie locale de chaque run

**Objectif** : garder une trace de chaque transcription pour comparer les runs entre eux (modèle, réglages, machine, temps).

**Pourquoi** : l'ADR reste muet sur deux points faute de mesures répétées, la qualité en anglais et la variation d'un run à l'autre (« Cloud Code » sort 1 fois dans l'ADR et 0 fois dans le run du README, même vidéo).

**Principe** : tout reste local, rien n'est envoyé hors de la machine. Un enregistrement par run, écrit en fin de job (réussi ou en erreur), dans un fichier JSON Lines sur un volume Docker nommé. Le texte de la transcription va dans un fichier séparé par run, pour garder l'index léger.

| Famille | Champs |
|---|---|
| Identité | identifiant du run, date de début (UTC), URL, identifiant de la vidéo, titre et durée de la vidéo |
| Résultat | état final (`done` ou `error`), message d'erreur, nombre de mots et de caractères, langue détectée et sa probabilité, chemin du texte |
| Modèle et réglages | modèle, `compute_type`, `beam_size`, `vad_filter`, `condition_on_previous_text`, `hotwords` |
| Temps | téléchargement, transcription, total, et le rapport durée de la vidéo sur temps de transcription |
| Machine | CPU (modèle, cœurs), RAM, GPU (nom, VRAM, driver, CUDA), OS, version de Docker |
| Versions | faster-whisper, CTranslate2, PyAV, yt-dlp |

**À trancher à l'implémentation**
- Lire le GPU via `nvidia-smi --query-gpu` dans le conteneur ou via `pynvml` (supposé : les deux marchent, non mesuré).
- Mesurer la VRAM de pic pendant le run, l'ADR ne l'a relevée que pour deux vidéos.
- Une page `/runs` en lecture seule pour consulter l'historique, ou seulement le fichier.

### 2. Nouveau design : thème frais à trois couleurs, clair et sombre

**Objectif** : sortir du tout bleu. Trois couleurs par thème : un fond neutre, une couleur d'action, une couleur d'accent pour les états comme la progression et le succès. L'erreur garde son rouge.

**Mode** : suit `prefers-color-scheme` par défaut, avec un bouton pour forcer clair ou sombre, choix gardé dans `localStorage`. Avec Tailwind v4 cela passe par une variante `dark` pilotée par une classe sur `<html>` (supposé : la syntaxe `@custom-variant` est à vérifier dans la doc au moment de l'écrire).

**Trois propositions à choisir.** Les valeurs sont un point de départ. Le contraste texte sur fond n'est pas mesuré, il se vérifie avant de choisir.

| Palette | Ambiance | Fond clair / sombre | Action | Accent |
|---|---|---|---|---|
| **A. Menthe et ardoise** | calme, technique | `#F6FAF9` / `#0F1A1A` | `#0D9488` | `#F59E0B` |
| **B. Lagon et corail** | vivante, chaude | `#FAF8F5` / `#14181F` | `#0891B2` | `#FB7185` |
| **C. Sauge et lavande** | douce, éditoriale | `#F7F8F4` / `#161A16` | `#4D7C5A` | `#8B5CF6` |

Ma préférence est la A : le vert d'eau tranche avec le bleu actuel, et l'ambre ressort sur fond sombre comme sur fond clair. La B est la plus contrastée, la C la plus sobre.

### 3. Tests e2e avec Playwright

**Objectif** : versionner dans le dépôt les vérifications de la page faites à la main pendant la revue du MVP, pour les rejouer à chaque changement du design ou de la télémétrie.

**Pourquoi** : les scripts de la revue vivent aujourd'hui hors du dépôt, et le nouveau design touche la page entière.

**Scénarios à couvrir**
- URL invalide : message lisible, bouton réactivé, application toujours vivante.
- Rechargement de la page pendant un job : la page reprend le suivi et affiche le texte final.
- Coupure réseau brève : « Connexion perdue, nouvelle tentative… », puis la fin normale.
- Job inconnu (404) : message clair, identifiant effacé.
- Copier : le presse-papiers contient tout le texte.

**Deux niveaux, parce que la CI n'a pas de GPU**
- **Niveau local, avec le vrai modèle** : Docker et GPU, le garde-fou avant fusion. Une vidéo courte suffit (`KnXm3PbNz5A`, 15 min, environ 30 s de transcription d'après l'ADR). Un montage jetable ne trouve que ce qu'on a pensé à y mettre, donc ce niveau ne se remplace pas.
- **Niveau CI, sans GPU** : la page et l'API tournent avec un transcripteur factice, ce qui couvre les cinq scénarios ci-dessus mais pas Whisper. Il demande un réglage explicite qui choisit le transcripteur factice (variable d'environnement, jamais actif par défaut), car `Transcriber` vise `cuda` en dur.

**À respecter**
- Lancer Playwright dans un conteneur, comme pour la revue, pour ne rien installer sur la machine. Chromium en root demande `--no-sandbox`.
- Coller avec `Shift+Insert` : mesuré pendant le MVP, `Ctrl+V` ne colle rien dans Chromium headless.
- Rangement et lanceur (dossier `tests/e2e/`, service Compose dédié ou commande `docker run`) à trancher à l'implémentation, avec `pytest-playwright` ou le script brut (supposé : les deux conviennent).

## Suggestions

Classées par intérêt, du plus rentable au plus lointain.

| # | Suggestion | Pourquoi |
|---|---|---|
| 4 | **Limite de durée sur un job** et refus des directs en cours (`/live/ID`) | relevé par la revue du MVP : un direct sans fin garderait le verrou pris jusqu'au redémarrage du conteneur (supposé, non mesuré) |
| 5 | **Titre, chaîne et durée de la vidéo** affichés dès le lancement | on vérifie qu'on a collé la bonne vidéo avant d'attendre plusieurs minutes |
| 6 | **Télécharger le texte en `.txt`**, avec le titre de la vidéo en première ligne | le texte part ensuite vers le skill de résumé, le titre lui sert de contexte |
| 7 | **Annuler un job en cours** | aujourd'hui un mauvais collage bloque le GPU jusqu'à la fin, et un second job reçoit un 409 |
| 8 | **CI GitHub Actions**, sans GPU : les 23 tests pytest et l'e2e Playwright avec transcripteur factice | le dépôt n'en a pas, la PR #1 a été validée à la main. Les runners GitHub standard n'ont pas de GPU (supposé, à vérifier dans la doc), donc le modèle réel reste testé en local avant fusion. Un runner auto-hébergé sur ta machine pourrait le lancer, mais sur un dépôt public il exécuterait le code des PR, à ne considérer que dépôt privé |
| 9 | **Healthcheck Compose** sur la fin du chargement du modèle | le premier démarrage télécharge 1,6 Go et la page n'est servie qu'après |
| 10 | **Hotwords modifiables depuis la page** | aujourd'hui il faut relancer le conteneur avec `HOTWORDS` |
| 11 | **Mesurer l'anglais** sur 2 ou 3 vidéos, avec un jeu de référence | l'ADR note la qualité en anglais comme supposée, non mesurée |
| 12 | **File d'attente de plusieurs URLs** | un seul GPU, donc traitement l'un après l'autre |
| 13 | **Brancher le skill de résumé** | hors MVP par décision, à reprendre une fois le texte et la télémétrie stables |
| 14 | **Traduction en aval** avec un petit modèle local | prévue comme étape ultérieure par l'ADR, `large-v3-turbo` ne traduit pas |

## Points ouverts du MVP

- La limite des réessais de la page (5 tentatives au total) a été gardée telle quelle.
- Les erreurs 4xx autres que 404 sont réessayées comme des 5xx. Sans effet tant que l'API ne renvoie que 404 sur `GET /jobs/{id}`.
- L'écart « Cloud Code » entre l'ADR et le README reste inexpliqué. La télémétrie (n° 1) doit aider à le mesurer.
