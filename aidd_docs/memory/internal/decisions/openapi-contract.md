# /openapi.json comme contrat de l'API

- Date: 2026-10-13
- Status: Accepted
- Replaces: la ligne « No OpenAPI spec is maintained » de l'ancien `aidd_docs/memory/api.md`, qui n'était pas un ADR

Issue #64, livrée par la PR #65.

## Contexte

Mesure faite le 2026-10-13 avec `create_app(...).openapi()` : FastAPI publiait déjà `/openapi.json` et `/docs`, mais le contrat était vide. Aucune route n'avait de `response_model`, donc chaque `200` et `202` avait `schema: {}`. Seul le corps `JobRequest` était typé, et les `404`, `409` et `422` maison n'étaient pas déclarés.

Le contrat vivait donc à la main, dans `api.md` et dans la section API du README, qui recopiaient chaque champ. Une copie à la main dérive du code sans que rien ne le signale.

## Décision

`/openapi.json` est le contrat de l'API, et `/docs` le rend lisible.

- Les modèles des réponses vivent dans `app/contract.py`, un par forme de réponse JSON, avec `extra="forbid"`.
- Les routes les déclarent par `responses=`, avec le media type des réponses qui ne sont pas du JSON (`/`, `/runs/{id}/markdown`, `/runs/{id}/frames/{name}`).
- `tests/test_contract.py` échoue si une route publie un schéma vide ou omet un code de sa table `EXPECTED`, et valide les vrais corps contre les modèles.
- `api.md` et le README renvoient vers `/docs` et ne gardent que ce que le schéma ne dit pas.

## Alternatives

- **`response_model=`** : FastAPI vérifierait la réponse à l'exécution, mais il filtre et re-sérialise les corps. Une réponse pourrait changer sans qu'on le veuille, alors que #64 exigeait des réponses identiques.
- **Un `openapi.json` versionné dans le repo** : une deuxième copie du contrat, qui dérive comme la doc à la main.
- **Garder la doc écrite à la main** : l'état d'avant, qui dérive.

## Risque accepté

Rien ne vérifie le schéma pendant que l'app tourne. C'est `tests/test_contract.py` qui garde l'accord entre le code et le contrat, à chaque CI.

Deux écarts du schéma sont gardés exprès, et tracés dans l'issue #66 (label `later`) :

- FastAPI ajoute un `422` à chaque route qui a un paramètre de chemin, et ce code ne se déclenche jamais.
- Le schéma annonce le défaut `"text"` pour `level`, alors que `JobRequest.level` vaut `None`. L'effet est le même.

Les corriger demande de surcharger la génération du schéma de FastAPI, pour un gain cosmétique. On les reprend seulement si un client généré depuis le schéma, ou un agent qui le lit, se trompe à cause de l'un d'eux.

## Conséquences

- Une route nouvelle ou un corps modifié touche `app/contract.py` et la table `EXPECTED` de `tests/test_contract.py` dans le même changement.
- `limit` et `offset` de `GET /runs` sont déclarés par `openapi_extra` et non par `Query(int)`, pour que leur `422` reste en français.
- Le `422` de `POST /jobs` décrit `detail` comme un texte ou une liste : un corps qui n'est pas du JSON valide reçoit encore la liste d'erreurs de pydantic.
- La section « Piloter l'app depuis un agent » du README s'appuie sur ce schéma pour les champs, et ne décrit que le cycle et quoi faire de chaque code.
