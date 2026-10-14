# File d'attente des jobs

- Date: 2026-10-14
- Status: Accepted
- Replaces: la phrase « Un second job reçoit un message clair » de la ligne « Attente côté UI » de `stack.md`, et le `409` de `POST /jobs` qu'elle promettait

Issue #12.

## Contexte

Il n'y a qu'un GPU, donc un seul job tourne à la fois. Jusqu'ici, un second `POST /jobs` pendant un job en cours recevait `409`. L'appelant, la page ou le skill `capture-video`, devait attendre la fin du premier job puis réessayer, ou s'arrêter.

## Décision

`POST /jobs` répond toujours `202` quand la requête est valide. Les jobs passent dans une file FIFO, traitée par un seul worker.

- Un thread worker unique, démarré par `create_app`, lit une `queue.Queue`. `create_job` enfile `(job, video_id, url)` et ne lance plus de thread.
- Un job reste en `queued` tant qu'il attend.
- L'horloge de la limite de durée (`Job.started`) repart quand le worker prend le job (`Job.begin()`). Attendre dans la file ne consomme pas les 15 minutes.
- Un job annulé pendant qu'il attend finit en `error` « Transcription annulée. », avec sa ligne `runs`, sans téléchargement : `work` appelle `job.check()` avant l'étape `downloading`.
- L'éviction des 20 jobs gardés en mémoire ne retire que des jobs finis, parce qu'un job en file évincé serait perdu sans trace.
- La file n'est pas bornée (supposé : un seul utilisateur, quelques URL à la fois).
- La page ne change pas (supposé : les critères de l'issue portent sur l'API). Soumettre plusieurs URL depuis la page est une suite à ouvrir.
- Le `409` de `POST /jobs/{id}/cancel` pour un job fini reste.

## Alternatives

- **Garder le `409` et laisser l'appelant réessayer** : l'état d'avant, chaque appelant réécrit sa boucle d'attente.
- **Un thread par job, bloqué sur un verrou** : rien ne garantit que les threads prennent le verrou dans l'ordre d'arrivée.
- **File bornée, `409` quand elle est pleine** : ramène le `409` pour un cas que le seul utilisateur ne rencontre pas.

## Risque accepté

Un redémarrage perd toute la file, comme il perdait le job en cours. Les jobs en attente n'ont pas de ligne `runs` tant que le worker ne les a pas traités.

## Conséquences

- `JobBusy` disparaît de `app/jobs.py`, et `POST /jobs` ne publie plus de `409` dans `/openapi.json`.
- Le store peut dépasser 20 jobs quand plus de 20 sont non finis, il ne retire que des jobs finis.
