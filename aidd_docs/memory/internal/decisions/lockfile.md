# Lockfile des dépendances Python et yt-dlp

- Date: 2026-10-07
- Status: Proposed
- Supersedes: `aidd_docs/memory/internal/decisions/stack.md`, ligne « Audio » (`yt-dlp` non figé), une fois cet ADR accepté

Prépare l'issue #25.

## Contexte

Les dépendances vivent dans `requirements.txt`, sans lockfile. Quatre des six lignes n'ont aucune version (`fastapi`, `uvicorn[standard]`, `yt-dlp`, `deno`). Deux conséquences mesurées le 2026-10-07 :

- **Trivy ne voyait qu'une dépendance sur six.** Il ne lit que les lignes `==` et ignore les transitives (doc `docs/guide/coverage/language/python.md`). La PR #21 ajoute donc une étape qui résout l'arbre complet à chaque scan.
- **Deux builds du même commit n'installent pas les mêmes versions.** Le piège PyAV de `stack.md` en est un exemple : la version 19 casse faster-whisper, et seule la borne `<16` protège.

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

## À vérifier avant d'accepter (supposé, non testé)

- `uv sync --frozen` dans le `python:3.12-slim` du `Dockerfile`, avec le groupe `gpu`, produit la même image qu'aujourd'hui. La taille et le démarrage GPU ne sont pas mesurés.
- Dependabot prend en charge `uv` et ouvre une PR sur `uv.lock`. Non lu dans sa doc.
- Après `uv pip install --upgrade yt-dlp`, `uv.lock` et l'image divergent sur cette seule version. Le scan Trivy voit la version verrouillée, pas celle de l'image. À accepter, ou à corriger.
- Le piège PyAV (`>=15,<16`) se déclare dans `pyproject.toml` et se retrouve dans le lock. Dependabot propose déjà `av>=19.0.1` dans la PR #24, qui casse faster-whisper d'après `stack.md`.

## Conséquences

- Deux builds du même commit installent les mêmes versions, sauf `yt-dlp`, qui suit YouTube comme avant.
- Le scan Trivy couvre l'arbre complet sans étape ajoutée au workflow.
- `Dockerfile`, `scripts/check.sh` et `requirements-dev.txt` changent. `requirements.txt` disparaît.
- Le lockfile s'ajoute au diff de chaque mise à jour de dépendance.
