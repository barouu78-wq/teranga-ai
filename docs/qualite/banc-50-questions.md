# Banc qualité : 50 questions

Créé le 22 novembre 2026 (ticket QA P0). Fichiers : `tests/banc_qualite/questions.json` (questions),
`scripts/banc_qualite.py` (exécution et notation), `tests/test_banc_qualite.py` (contrôles gratuits dans le CI).

## Statut

- **Exécuté** : le mode hors ligne, sans IA ni réseau, le 22 novembre 2026 sur le code de la branche. 50/50
  questions passent après la correction de la réponse prête sur le paludisme (voir plus bas).
- **Exécuté en réel** : le 22 novembre 2026, sur https://teranga-ai.fr, par GitHub Actions (workflow
  `banc-qualite-reel`). 50 réponses, aucune en échec ni dégradée, aucune hallucination grave détectée. Note proposée
  par Claude, **à valider par un humain** : 94,1/100. Détails : `docs/qualite/resultats-2026-11-22.md`.

## Les 10 catégories (5 questions chacune)

Vie quotidienne · Transport · Emploi et formation · Entrepreneuriat · Santé et urgences · Tourisme · Diaspora ·
Compréhension de contexte (question vague, fautes de frappe, information qui change, donnée personnelle, sujet
politique) · Langues (français, anglais, wolof) · Conversation et suivi (questions qui dépendent de l'échange
précédent, avec un historique).

21 questions sont marquées **critiques** (santé, urgences, argent, démarches officielles, droit, données
personnelles) : une affirmation interdite y compte comme hallucination grave.

## Ce qui est automatique, ce qui demande un humain

| Contrôle | Automatique | Humain |
|---|---|---|
| La base vérifiée du site fournit les faits utiles (contexte de l'IA ou réponse prête) | oui, gratuit, dans le CI | |
| Réponses prêtes (sans IA) : attendus présents, aucun interdit | oui, gratuit, dans le CI | |
| Réponse de l'IA : attendus présents (expressions régulières) | oui, mode réel | relire : un attendu absent n'est pas toujours une faute |
| Réponse de l'IA : interdits (faux numéro d'urgence, numéro de téléphone inventé, dose en mg, tarif sur une démarche…) | signalé « à confirmer » | confirmer ou rejeter |
| Exactitude, compréhension, contexte Sénégal, utilité, clarté (25/20/20/20/15) | non | oui, fiche CSV |
| Réponses en wolof | non | un locuteur du wolof |

Chaque attendu vient d'un fait déjà sourcé dans le dépôt (`services/practical_facts.py`, `services/events.py`,
`data/senegal_knowledge.json`, `services/quick_answers.py`) : le banc n'ajoute aucun fait.

## Lancer

```bash
# 1. Gratuit : base vérifiée et réponses prêtes (aussi lancé par pytest)
OPENAI_API_KEY=test-key python scripts/banc_qualite.py hors-ligne

# 2. Payant, avec l'accord du propriétaire : vraies réponses
python scripts/banc_qualite.py reel --site https://teranga-ai.fr     # site en ligne, 6 s entre deux questions
#    ou, sans ordinateur : GitHub → Actions → banc-qualite-reel → Run workflow (rapport et fiche en artefact)
python scripts/banc_qualite.py reel --local                          # ce code, clés dans l'environnement (Render → Shell)
#    → banc-qualite-<date>.md (réponses, contrôles, temps) et banc-qualite-<date>.csv (fiche à remplir)

# 3. Gratuit : la note, une fois la fiche remplie (Excel, séparateur « ; »)
python scripts/banc_qualite.py noter banc-qualite-<date>.csv
```

Mode `--site` : 50 questions comptent dans le plafond `AI_PLAFOND_JOUR` (500 par jour par défaut) et dans les limites
de débit du site (16 par minute, 120 par heure par visiteur) ; le script attend 6 s entre deux questions. Les
réponses prêtes (urgences, conversions) ne coûtent rien.

## Objectif

Moyenne d'au moins **85/100**, **zéro hallucination grave** confirmée, toutes les questions notées. Une question non
notée n'est jamais comptée 0 : elle est listée et l'objectif n'est pas atteint tant qu'elle manque.

## Défauts déjà trouvés par le mode hors ligne

- **Paludisme (corrigé dans la même PR)** : « Paludisme : comment se protéger ? » recevait une réponse prête d'une
  ligne (« protection anti-moustiques et avis d'un médecin »), alors que le dépôt a une ligne vérifiée de prévention
  (moustiquaire imprégnée d'insecticide, répulsif, vêtements couvrants, avis médical avant le départ). Les questions
  de protection reçoivent maintenant cette ligne ; « Y a-t-il le paludisme au Sénégal ? » garde la ligne générale.

## Limites connues

- Les expressions régulières sont un repère grossier : la fiche humaine fait foi.
- Les temps mesurés par le mode réel portent sur 50 questions : une médiane, pas un p95 fiable.
- Le jeu de 50 questions est fixe : le compléter quand un défaut réel est signalé, sans retirer de question.
