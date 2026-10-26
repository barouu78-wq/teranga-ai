# Sécurité P1-4 — plafond quotidien de dépense IA

## Politique

- Budget global partagé entre OpenAI et Anthropic : **5 EUR par jour**.
- Fenêtre journalière UTC, renouvelée à minuit UTC.
- Chaque génération texte réserve atomiquement un montant dans Redis avant l'appel fournisseur.
- À la limite, l'appel est refusé. Les réponses locales et les réponses de secours sans IA peuvent toujours fonctionner.
- En production, si Redis est absent ou en panne, les nouveaux appels IA sont refusés (fail closed).
- Si le fournisseur ne retourne pas l'usage final, la réservation entière est imputée par prudence.
- La voix STT/TTS réserve un montant prudent fixe avant l'appel. La session vocale WebRTC en direct est refusée en production : son usage continue directement entre le navigateur et OpenAI, hors du processus qui mesure les coûts. La réactiver exige un mécanisme fiable de durée/usage ou une limite dure côté fournisseur.

## Implémentation

Le hash quotidien `teranga:ai-spend:AAAA-MM-JJ` conserve `used`, `reserved` et les réservations individuelles. Le script Lua d'admission vérifie puis incrémente `reserved` en une seule opération ; deux workers ne peuvent donc pas consommer simultanément le même solde. La finalisation retire la réservation et ajoute le coût estimé à `used`.

Les coûts sont conservés en micro-euros. La conversion USD/EUR utilise volontairement 1:1, ce qui est conservateur pour l'admission. Les entrées sont estimées en comptant chaque octet UTF-8 comme un token, avec une marge de 25 %, et la sortie est bornée par `max_output_tokens`. Les tarifs connus sont codés dans `services/ai_spend.py`; un modèle inconnu utilise une estimation élevée. Il faut revoir cette table lorsque les modèles ou leurs tarifs changent.

Ce contrôle applicatif est une protection contre les abus, pas un substitut aux budgets et alertes configurés dans les consoles OpenAI et Anthropic. Une facture fournisseur peut aussi inclure des éléments non exposés par les usages de réponse ; garder les plafonds fournisseur activés.

## Sources officielles consultées

- OpenAI API pricing : https://developers.openai.com/api/docs/pricing
- Anthropic Claude Opus 5.5 API pricing : https://www.anthropic.com/claude-opus-5-5

## Tests attendus

- Plusieurs réservations concurrentes ne peuvent pas dépasser le plafond.
- OpenAI et Anthropic utilisent la même clé quotidienne.
- Une panne Redis ou l'absence de Redis en production bloque l'appel.
- Un usage final absent consomme la réservation au lieu de la libérer.
