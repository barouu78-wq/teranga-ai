---
name: carte-du-code
description: Construire et interroger la carte du code de Teranga AI avec graphify (liens entre fichiers, fonctions et tests), en local et sans IA. À utiliser avant de modifier un endroit mal connu, pour savoir ce qui dépend d'une fonction, ou quand le propriétaire demande une vue d'ensemble du code.
---

# Carte du code (graphify)

Graphify lit le code en local (arbres syntaxiques, sans modèle d'IA) et produit une carte dans `graphify-out/` :
`graph.json` (interrogeable), `graph.html` (page interactive) et `GRAPH_REPORT.md` (éléments centraux, ponts entre
parties du code, questions suggérées). Le code n'est envoyé à personne.

Choix du propriétaire du 12 octobre 2026 : version fixée, installée à part dans chaque session, **aucun crochet**.

## Installer (à part, version fixée)
Dans le dossier de travail temporaire de la session (ici `/tmp` pour l'exemple) :
```bash
python -m venv /tmp/graphify-venv
/tmp/graphify-venv/bin/pip install -q graphifyy==0.9.86   # nom du paquet : deux « y »
```

## Construire la carte
Depuis une copie propre de `main`, pour ne pas cartographier des fichiers non suivis :
```bash
git fetch origin main -q
rm -rf /tmp/teranga-carte && mkdir -p /tmp/teranga-carte
git archive origin/main | tar -x -C /tmp/teranga-carte
cd /tmp/teranga-carte && /tmp/graphify-venv/bin/graphify update .
```
Le 12 octobre 2026 (`main` 6aa327e) : 294 fichiers, environ 4 000 éléments, 8 800 liens, 209 groupes, en moins d'une minute.
Si la carte est construite dans le dépôt lui-même, `graphify-out/` est ignoré par git : ne jamais le commiter.

## Interroger
```bash
G=/tmp/teranga-carte/graphify-out/graph.json
/tmp/graphify-venv/bin/graphify explain "parse_chat_payload()" --graph $G          # ce qui est relié à un élément
/tmp/graphify-venv/bin/graphify path "parse_chat_payload()" "format_senegal_knowledge()" --graph $G
```
Puis lire `GRAPH_REPORT.md` :
- **God Nodes** : les éléments les plus reliés (le 12 octobre : `parse_chat_payload()`, `VoiceBench`,
  `build_intent_context()`, `build_agent_plan()`, `build_chat_service()`). Y toucher demande le plus de tests.
- **Surprising Connections** et **Suggested Questions** : pistes à vérifier, pas des faits.

## Règles
- **Jamais `graphify install`** (ni `--project`) : cette commande ajoute des crochets qui exécutent graphify avant
  chaque action de Claude et de tous les agents, et modifie les réglages du projet. Refusé par le propriétaire.
- **Jamais `graphify add`, `graphify clone` ni le mode `/graphify` avec un modèle** : ils récupèrent des contenus du web
  ou envoient des documents à un modèle. Ne jamais définir `GEMINI_API_KEY` ni `GOOGLE_API_KEY` pour graphify.
- Changer de version de graphify passe par une PR qui met à jour la version ici ; `tests/test_carte_du_code.py`
  vérifie qu'elle reste fixée.
- La carte guide, elle ne prouve rien : les liens marqués `INFERRED` sont devinés. Vérifier dans le code avant
  d'affirmer quoi que ce soit.
- Pour le propriétaire : `graph.html` s'envoie tel quel ; la page charge `vis-network` depuis unpkg.com.
