# Lockfile des dépendances Python et yt-dlp

- Date: 2026-10-07
- Status: Accepted
- Supersedes: `aidd_docs/memory/internal/decisions/stack.md`, ligne « Audio » (`yt-dlp` non figé), une fois cet ADR accepté

Prépare l'issue #25.

## Contexte

Les dépendances vivent dans `requirements.txt`, sans lockfile. Quatre des six lignes n'ont aucune version (`fastapi`, `uvicorn[standard]`, `yt-dlp`, `deno`). Deux conséquences mesurées le 2026-10-07 :

- **Trivy ne voyait qu'une dépendance sur six.** Il ne lit que les lignes `==` et ignore les transitives (doc `docs/guide/coverage/language/python.md`). La PR #21 ajoute donc une étape qui résout l'arbre complet à chaque scan.
- **Deux builds du même commit n'installent pas les mêmes versions.** Le piège PyAV de `stack.md` en est un exemple : la version 19 casse faster-whisper, et seule la borne `<19` protège.

`stack.md` demande que `yt-dlp` reste libre, parce que YouTube change souvent et qu'un `docker compose build --no-cache` suffit à suivre. Un lockfile fige justement ce que cette règle laisse flotter.

Les paquets `nvidia-cublas-cu12` et `nvidia-cudnn-cu12==9.*` sont installés dans le `Dockerfile`, hors de `requirements.txt`. Ils n'apparaissent ni dans le fichier résolu ni dans le scan.

## Décision

On passe à `uv`, avec `pyproject.toml` pour la déclaration et `uv.lock` pour le graphe figé, lu directement par Trivy. `yt-dlp` est verrouillé comme le reste, puis mis à jour au build par `uv pip install --upgrade yt-dlp`, et les paquets `nvidia-*` entrent dans un groupe `gpu` de `pyproject.toml`. Dependabot met le lock à jour, écosystème `uv`.

## Alternatives

- **`pip-compile`** : produit un `requirements.txt` figé que Trivy lit, mais le gestionnaire et la déclaration restent séparés.
- **`poetry`** : plus lourd pour un outil à un seul service.
- **Garder l'étape de résolution du workflow** : fonctionne (PR #22 jetable), mais duplique ce que le lockfile fait déjà.
- **Épingler `yt-dlp` sans mise à jour** : un rebuild ne suivrait plus YouTube, ce que `stack.md` interdit.
- **Exclure `yt-dlp` du lock** : Trivy ne le verrait plus.
- **Laisser les `nvidia-*` dans le `Dockerfile`** : hors lockfile, donc hors scan.
- **Mettre le lock à jour à la main** : il se périme sans alerte.

## Vérifications faites le 2026-10-07

- **Dependabot** gère l'écosystème `uv` pour les mises à jour de version (doc `supported-package-managers.md`). Pour les mises à jour de sécurité, la doc dépend d'un drapeau GitHub, non confirmé pour ce dépôt.
- **Build** : `uv sync --frozen --no-install-project --no-dev --group gpu` dans `python:3.12-slim` passe en 2 min, image de 4,77 Go contre 4,76 Go aujourd'hui. Sans `--no-dev`, `uv sync` installe le groupe `dev` par défaut et l'image grossit de 0,4 Go (ruff, pyright, pytest).
- **GPU** : dans cette image, `entrypoint.sh` trouve les libs `nvidia-*`, `ctranslate2` voit 1 GPU, et la vidéo `KnXm3PbNz5A` (15 min) est transcrite en 35 s, 3 680 mots, sans erreur. `stack.md` mesure 30 s avec l'image actuelle.
- **PyAV** reste en `15.1.0` dans le lock, avec la borne `<19`. La PR #24 propose `av>=19.0.1`, qui casse faster-whisper d'après `stack.md`.

## Risque accepté

Après `uv pip install --upgrade yt-dlp`, l'image porte une version de `yt-dlp` plus récente que `uv.lock`, et Trivy scanne celle du lock. Le build ne fait que monter la version, donc Trivy voit au pire une version plus ancienne (un faux positif, pas une faille manquée). Ce raisonnement suppose qu'une version plus récente n'introduit pas de faille, il n'est pas mesuré. Dependabot sur `uv.lock` borne l'écart à une semaine.

## Conséquences

- Deux builds du même commit installent les mêmes versions, sauf `yt-dlp`, qui suit YouTube comme avant.
- Le scan Trivy couvre l'arbre complet sans étape de résolution. Trivy traite tout `[dependency-groups]` comme des dépendances de dev et les ignore, y compris `gpu` (mesuré sur 0.70.0, le défaut de trivy-action). Le workflow pose donc `TRIVY_INCLUDE_DEV_DEPS: 'true'`, et ruff, pyright et pytest sont scannés aussi.
- `Dockerfile` et `scripts/check.sh` changent, `requirements.txt` et `requirements-dev.txt` disparaissent. `uv` est épinglé à la même version dans les deux.
- Le lockfile s'ajoute au diff de chaque mise à jour de dépendance.
