# Review: serve-frames (#52)

- **Verdict**: approve
- **Diff**: `main...feat/serve-frames` (11a282a, 142c5de, 068a8c5)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_12
- **Findings**: 0 critical, 0 warning, 4 minor

## Phases

### Phase 1 — Route des images, champ `url`, tests et mémoire

- [x] Task 1, `frame_file` ne rend un chemin que pour un nom listé dans la base et présent sur le disque — `app/runs.py:246-262`, `tests/test_runs.py:454-462` (`../runs.db`, `runs.db`, `frames/{id}/0000.webp` rendent `None`)
- [x] Task 2, `curl /runs/{id}/frames/0000.webp` rend l'image, `404` en français pour une image ou un run inconnus — `app/main.py:207-214`, live curl en `YT_FAKE=1` : `200 image/webp`, octets `RIFF....WEBP`, `404 {"detail":"Image inconnue."}`, `404 {"detail":"Run inconnu."}`
- [x] Task 3, `GET /runs/{id}` et `/runs/latest` listent chaque image avec `time` et `url` — `app/main.py:34-38`, `:198`, `:205`, `tests/test_runs.py:402-412`, live `jq .frames` sur `/runs/latest`
- [x] Task 4, `scripts/check.sh` passe, couverture au-dessus de 80 % — relancé : `113 passed`, `Total coverage: 92.15%`
- [x] Task 5, aucune ligne du README ni de la mémoire n'annonce encore la route « à venir avec #52 » — `grep -n "#52"` sur `README.md` et `aidd_docs/memory/*.md` : seule `api.md` est touchée, plus aucune mention ; `internal/decisions/run-storage.md:35` cite déjà la route

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 1 | `app/main.py:209` | Seule requête SQL brute de `main.py` (`runs.query("SELECT 1 FROM runs ...")`), alors que toutes les autres routes passent par une méthode de `RunStore` et que le plan range le stockage dans `RunStore` | Ajouter `RunStore.has_run(run_id) -> bool` et l'appeler dans la route |
| 🟢 minor | code | 1 | `tests/test_runs.py:447-452` | Le run `a` n'existe pas, donc la requête HTTP sort par la branche « Run inconnu. ». La branche route `:memory:` → « Image inconnue. » n'est pas exercée, et le test n'asserte que le statut | Lancer un job sur `RunStore(":memory:")`, puis `GET /runs/{id}/frames/0000.webp` et asserter `{"detail": "Image inconnue."}` |
| 🟢 minor | code | 1 | `tests/test_runs.py:409` | La boucle de téléchargement lit `run`, la variable restée de la boucle précédente (donc `/runs/latest` seul) | Télécharger dans la première boucle, ou nommer explicitement la réponse visée |
| 🟢 minor | rot | 1 | `aidd_docs/memory/api.md:18` | « `../runs.db` matches nothing » laisse croire que la liste blanche répond. En live, `..%2Fruns.db` rend le 404 générique anglais `{"detail":"Not Found"}` (route jamais atteinte), en écart avec `api.md:24` « written in French » | Préciser qu'un `/` encodé n'atteint pas la route et reçoit le 404 générique de Starlette |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (5/5)                                        |
| Files checked | app/main.py, app/runs.py, tests/test_runs.py, README.md, aidd_docs/memory/api.md, aidd_docs/memory/codebase-map.md, aidd_docs/memory/architecture.md, aidd_docs/memory/internal/decisions/run-storage.md |
| Unchecked     | none                                              |
| Unplanned     | none                                              |

## Follow-up

The four minor findings and the README suggestion were applied after the review: `RunStore.has_run` replaces the raw SQL of the route, the `:memory:` test runs a known job and checks `Image inconnue.`, every frame of both responses is downloaded, `api.md` says an encoded `/` gets the generic Starlette 404, and the README shows a `curl` on an image. `scripts/check.sh`: `113 passed`, `Total coverage: 92.20%`. `HEAD` on an image still gives `405`, no criterion asks for it.
