---
objective: "Les seuils de capture des slides et la méthode de détection reposent sur des mesures faites sur gsxiFd8AZQU et KnXm3PbNz5A, consignées dans l'ADR frames-pyav.md."
status: implemented
---

# Plan: calibrer les seuils de capture des slides

Source: issue kevpdev/yt-transcriber#53

## Phases

| #   | Phase | File | Depends on |
| --- | ----- | ---- | ---------- |
| 1   | banc de calibrage rejouable | [`phase-1.md`](./phase-1.md) | none |
| 2   | mesures et relecture à l'œil | [`phase-2.md`](./phase-2.md) | 1 |
| 3   | appliquer les seuils et consigner | [`phase-3.md`](./phase-3.md) | 2 |

## External sources

| URL | What it settled |
| --- | --------------- |
| https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect | La variable `scene` du filtre `select` vaut entre 0 et 1, c'est la valeur que le banc lit pour le filtre de scène |
| https://pyav.basswood-io.com/docs/stable/api/filter.html | PyAV expose `av.filter.Graph` (`add_buffer`, `add`, `link_to`, `push`, `pull`), donc un graphe `select` tourne sans binaire. Non essayé dans l'image, la phase 1 le vérifie |

## Impact

| Category | Verdict and evidence | Handled in |
| -------- | -------------------- | ---------- |
| runtime | Le banc télécharge deux flux vidéo depuis YouTube (environ 38 Mo pour KnXm3PbNz5A en AV1 720p, environ 140 Mo extrapolés pour gsxiFd8AZQU, chiffres de l'ADR). gsxiFd8AZQU n'a jamais été capturée : aucun run `frames` sur cette vidéo dans `data/runs.db`, lu le 2026-11-09. Non vérifié qu'elle propose AV1 ou VP9 | 1 |
| regression | Changer les constantes de `app/frames.py` touche `select_frames`, couvert par 11 tests de `tests/test_frames.py`. Deux tests dépendent de `HASH_DISTANCE` (`test_dhash_is_stable_and_tells_patterns_apart`, `test_two_screens_on_one_template_are_both_selected_without_dedupe`). Risque faible, pas de phase filet : les tests existants verrouillent déjà le comportement | 3 |
| regression | Référence avant changement : KnXm3PbNz5A donne 49 images à chacun des 6 runs `frames` de `data/runs.db`. Le banc doit retrouver 49 avec les seuils actuels, sinon il ne reproduit pas l'app | 1 |
| architecture | none, si la détection numpy est retenue. Si le filtre de scène gagne, le remplacement de `select_frames` sort du périmètre de ce plan (voir Decisions) | 2 |
| documentation | `frames-pyav.md` : section de calibrage et lignes « Supposé, non mesuré » tranchées. Commentaire « Provisional values » de `app/frames.py`. README section « Capturer les slides à la main » si le banc s'y ajoute. `codebase-map.md` liste `scripts/` : à compléter avec le banc | 3 |

## Rules

| Rule | Why it applies |
| ---- | -------------- |
| `coding-assertions.md` : ruff et pyright ne couvrent que `app` et `tests`, couverture à 80 % | Le banc vit dans `scripts/`, hors de la couverture, donc il ne fait pas baisser le seuil |
| `coding-assertions.md`, Language : code et commentaires en anglais | Le banc et ses sorties CSV sont en anglais, l'ADR reste en français |
| `architecture.md` : « A change that departs from the ADR needs a new ADR first » | Le filtre de scène figure déjà dans les alternatives de `frames-pyav.md`. Le retenir ne contredit pas l'ADR mais change l'implémentation, d'où l'arrêt prévu en phase 2 |
| CLAUDE.md, Keep the memory true | L'ADR et les fichiers mémoire qui citent les seuils suivent dans la phase 3 |

## Decisions

| Decision | Why |
| -------- | --- |
| Le banc rejoue `select_frames` de l'app en surchargeant ses constantes de module, sans dupliquer l'algorithme | Une copie divergerait de l'app au premier changement, et la mesure ne vaudrait plus pour le code livré |
| Le décodage se fait une seule fois par vidéo, les échantillons sont mis en cache (miniatures, dHash, image réduite) puis chaque jeu de seuils est rejoué sur le cache | Décoder 56 min par combinaison rendrait le balayage trop long |
| Si le filtre de scène sort meilleur, le plan s'arrête après la phase 2 avec les chiffres, et le remplacement fait l'objet d'une nouvelle issue | Remplacer la détection est un changement d'implémentation que #53 ne demande pas, seulement de choisir sur des chiffres |
| La relecture à l'œil se fait sur des planches contact : une planche de référence à une image toutes les 5 s, une planche des images retenues par jeu de seuils candidat | Relire 56 min de vidéo n'est pas tenable, une planche se compare en quelques minutes. Supposé suffisant pour repérer une slide manquée qui tient plus de 5 s |
