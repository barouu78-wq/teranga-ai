---
name: kit-de-la-semaine
description: Transformer les brouillons marketing de la semaine (docs/communication/<année>-S<semaine>.md, souvent dans une PR brouillon « communication/… ») en kit court prêt à copier-coller sur téléphone, avec un texte par jour et par réseau (chaîne WhatsApp, groupes de la diaspora, Instagram, TikTok et Reels), faits et liens vérifiés. À utiliser chaque lundi, et dès que le propriétaire demande quoi poster, des textes pour WhatsApp ou Instagram, un kit de publication, ou veut « travailler la visibilité » de Teranga, même sans dire « kit ».
---

# Kit de la semaine : du brouillon au copier-coller

Recette du 27 octobre 2026 (kit de la semaine 44). Le pôle `communication` écrit chaque lundi un long brouillon sourcé ;
le propriétaire, souvent sur son téléphone, a besoin d'une liste courte qu'il copie et publie lui-même. Ce skill fait le
passage de l'un à l'autre **sans rien publier** et sans ajouter un seul fait non vérifié.

## 1. Trouver le brouillon de la semaine
Le fichier vit d'abord sur la branche de la PR brouillon de l'agent `communication`, pas sur `main` :
```bash
git fetch -q origin main
git branch -r | grep -E "communication/|marketing/" | sort | tail -3   # la semaine la plus récente
git show origin/communication/2026-S44:docs/communication/2026-S44.md > <scratchpad>/S44.md
```
Lire le fichier **en entier** : la section « Limites », les sources (`[F2]`, `[D4]`…), la section « Écarté » et les
« Décisions demandées au propriétaire ». Lire aussi le brouillon de la semaine précédente pour ne pas republier un sujet.

## 2. Garder seulement ce qui peut partir tel quel
- **Jours à venir seulement** : la date du jour à Dakar (UTC) décide ; un jour passé est retiré, pas décalé en silence.
- **Chaque fait garde sa source** du dépôt (`services/practical_facts.py`, `data/senegal_knowledge.json`,
  `services/events.py`) ou d'une page officielle citée. Relire le passage cité : un chiffre absent de la source sort du kit.
- **Aucun prix, horaire, frais, statistique d'audience, témoignage ni avis** (règle d'`AGENTS.md`). Les mentions
  « à vérifier » restent dans le texte publié.
- **Fêtes lunaires** : la date reste « estimée » tant qu'elle n'est pas confirmée (`services/events.py`).
- **Wolof** : seulement les formules déjà présentes dans le dépôt, et le propriétaire les relit.
- **Partenaires** : aucun établissement présenté comme partenaire sans accord écrit ; pas de logo d'une autre marque.
- **Nouveauté vérifiée de la semaine** : `git log --since="7 days ago" origin/main --oneline` ; un fait nouveau et sourcé
  (exemple du 27 octobre : le TER jusqu'à l'AIBD, source APS, #546) peut remplacer une astuce plus faible. Le dire.

## 3. Vérifier chaque lien du site
Tout lien `teranga-ai.fr/…` du kit doit répondre 200 sur la version actuelle de `main` :
```bash
for p in /lieux /specialites-senegal /demarches-senegal /calendrier-fetes-senegal /transport-senegal; do
  printf "%s : " "$p"
  OPENAI_API_KEY=test-key python -c "import app; print(app.app.test_client().get('$p', base_url='https://teranga-ai.fr').status_code)" 2>/dev/null | tail -1
done
```
Un lien qui ne répond pas 200 est remplacé par `teranga-ai.fr`. Le propriétaire ouvre quand même chaque lien avant
d'envoyer (le site en ligne peut avoir un déploiement de retard).

## 4. Écrire le kit (dans la conversation, en français, tutoiement)
Le propriétaire lit sur son téléphone : un bloc de code par texte, pour le bouton « copier ». Gabarit :

```
### Mardi 27 · chaîne WhatsApp
(bloc de code : le texte exact, lien compris)

### Vendredi 30 · Instagram
Image : (ce qu'il faut photographier ou capturer : une vraie capture du site, ou une photo prise par le
propriétaire sans visage reconnaissable)
(bloc de code : la légende et les hashtags)
```
- Une ligne d'introduction : la période couverte et « Avant de publier, ouvre chaque lien une fois ».
- Les messages pour les **groupes de la diaspora** : « une seule fois par groupe, si les règles du groupe le permettent ».
- Les **vidéos** du brouillon : une ligne chacune, et l'offre de les fabriquer avec `video-reponse` (vrais écrans,
  réponse réellement capturée) ; elles coûtent du crédit, donc on demande avant.
- Terminer par la mesure : le nombre de questions au chat des **7 derniers jours**, comparé aux 7 jours d'avant. L'agent
  `analyste` le compte dans les journaux Render (lignes `latence route=chat`). `/stats-ia` montre un total **glissant sur
  30 jours** (`CoverageLog.summary()`) : ne jamais le présenter comme le chiffre de la semaine.
- Ne pas recopier les sources dans le kit : elles restent dans le brouillon et dans ta réponse si on te les demande.

## 5. Ce que le skill ne fait jamais
- Publier, programmer ou envoyer quoi que ce soit (Metricool, Instagram, WhatsApp, e-mail) : le propriétaire publie.
- Fusionner la PR brouillon de `communication` sans le « Go » du propriétaire : c'est son texte de marque.
- Annoncer un lien « vérifié » sans avoir lancé la commande de l'étape 3.
