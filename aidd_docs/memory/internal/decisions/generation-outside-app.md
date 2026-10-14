# Deux portes d'usage et génération hors de l'app

- Date: 2026-10-12
- Status: Accepted

Source : `aidd_docs/tasks/2026_10/2026_10_09_summary-modes/analysis.md`, sections Verdict, Q4, Q5, Q6 et « Usage agentique ». Porté par #49, #54 et, côté vault, #46.

## Contexte

L'outil doit servir trois modes de sortie : texte brut, résumé, résumé illustré. Les deux derniers demandent un LLM. Le brief exclut tout compte, quota et service payant, et l'app tourne sur le GPU de l'utilisateur, déjà occupé par Whisper.

L'app doit aussi servir un humain et un agent. Le résumé part vers le vault de l'utilisateur, hors de ce dépôt.

La doc Anthropic, page Legal and compliance, lue le 2026-10-09, dit que l'authentification OAuth « *is designed to support ordinary use of Claude Code and other native Anthropic applications* », et que les développeurs de produits, Agent SDK compris, « *should use API key authentication* ».

## Décision

La chaîne a trois maillons, chacun avec une seule responsabilité :

| Maillon | Fait | Ne fait pas |
|---|---|---|
| yt-transcriber | transcription horodatée, avec ou sans images, gardée par run | aucun LLM, aucune génération, ignore le vault |
| skill de transcription du vault (`capture-video` réécrit) | pilote l'app par l'API et rend la transcription et les images | aucune note dans le vault |
| skill de génération du vault (nouveau) | pose ses questions de cadrage, appelle le skill de transcription, produit un HTML puis, au besoin, un PDF, propose une note d'index | aucune transcription |

L'app a deux portes : la page pour l'humain, l'API HTTP pour l'agent, documentée comme un contrat (#54). L'app ne porte ni LLM ni identifiant d'abonnement. La génération se fait dans une session d'agent que l'utilisateur lance lui-même. Un serveur MCP est différé.

## Alternatives

- **`claude -p` dans le conteneur avec `CLAUDE_CODE_OAUTH_TOKEN`** : faisable, mais un identifiant d'abonnement stocké dans l'app sort de l'usage ordinaire, et un binaire s'ajoute à l'image. Le mode `--bare`, recommandé pour les scripts, ne lit pas ce jeton (doc, page Authentication).
- **Conteneur qui appelle le `claude` de l'hôte** : demande un démon hôte à écrire et à sécuriser.
- **API Anthropic avec clé** : service payant à l'usage, exclu par le brief.
- **Modèle local (Ollama) appelé par l'app** : respecte le brief et permettrait un bouton dans la page, mais ajoute un service, partage les 16 Go de VRAM avec Whisper, et sa qualité n'est pas mesurée.
- **PDF généré dans l'app avec WeasyPrint** : sans objet, puisque la génération sort de l'app.
- **Serveur MCP dans l'app** : apporterait la découverte des outils et le retour des images en contenu natif. À reprendre si un agent visé n'a pas de shell pour appeler l'API.
- **Skill de génération qui appelle l'app sans skill de transcription** : la transcription sert aussi seule, et un agent doit pouvoir la demander sans passer par la génération.

## Supposé, non mesuré

- Aucun agent visé ne manque d'un shell pour appeler l'API avec `curl`.
- Le quota de l'abonnement absorbe les images envoyées au modèle.

## Conséquences

- L'app n'ajoute aucune dépendance de génération et reste utilisable seule.
- Les modes résumé ne partent pas d'un bouton de la page, mais d'une session d'agent.
- L'utilisateur et un agent partagent le même job unique, donc le refus `409` sera plus fréquent, ce qui donne du poids à la file de #12 (résolu : la file existe, `job-queue.md` remplace le `409`).
- Le contrat d'API devient une interface publique : un changement de forme casse les skills du vault.
- La réécriture de `capture-video`, le skill de génération et le rangement du document dans le vault se décident côté vault.
