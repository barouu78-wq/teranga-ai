# Claude : IA de secours ou IA principale

Teranga AI utilise OpenAI. Avec une clé Anthropic, **Claude** peut :

- **servir de secours** (réglage par défaut) : si OpenAI ne répond pas (panne, surcharge, délai),
  le chat et le planificateur demandent automatiquement la réponse à Claude ;
- **devenir l'IA principale** : Claude répond à tout, avec sa propre recherche web, et OpenAI
  devient le secours.

Sans clé, rien ne change : le site répond avec OpenAI, puis avec sa base de connaissances.

## Activer

1. Va sur **platform.claude.com**, choisis **Individuel**, ajoute un moyen de paiement
   (**Billing**, quelques dollars de crédit suffisent pour commencer), puis crée une clé API
   (**API Keys** → **Create Key**). Ne l'envoie à personne, ni par message ni par e-mail.
2. Sur **Render** → ton service → **Environment** → **Add Environment Variable** :
   - Key : `ANTHROPIC_API_KEY`
   - Value : colle la clé
3. **Save Changes**. Le site redémarre en une minute. Claude est alors le **secours**.

## Choisir l'IA principale

Sur Render, ajoute (ou modifie) la variable :

| `AI_PRINCIPALE` | Effet |
|---|---|
| `openai` (ou absente) | OpenAI répond, Claude prend le relais en cas de panne |
| `claude` | Claude répond (avec recherche web), OpenAI prend le relais en cas de panne |

Pour revenir en arrière, remets `openai` : effet en une minute, sans redéploiement de code.

Optionnel : `ANTHROPIC_MODEL` choisit le modèle Claude. Par défaut `claude-opus-5-5` (le plus
capable) ; `claude-sonnet-5-5` coûte moins cher et répond un peu plus vite.

## Comparer avant de choisir

Le script `scripts/compare_ai.py` pose les **50 questions du banc d'essai** aux deux IA et écrit
`comparatif-ia.md` : réponses côte à côte, temps de réponse, faits attendus trouvés, jetons et coût.

1. Render → ton service → **Shell** (ou ton ordinateur avec les deux clés).
2. Essai rapide : `python scripts/compare_ai.py --limite 5`
3. Complet : `python scripts/compare_ai.py --prix-openai ENTREE,SORTIE --prix-claude ENTREE,SORTIE`
   (prix en dollars par million de jetons, lus sur les pages de tarifs d'OpenAI et d'Anthropic).

Le comparatif complet fait environ 100 appels : il coûte quelques dollars au plus.

## Ce qui est couvert

- Chat : réponse écrite complète. Les photos et la carte viennent d'autres services et restent
  les mêmes quelle que soit l'IA.
- Planificateur : itinéraire complet.
- La voix (dictée, lecture) reste toujours sur OpenAI.

Journaux Render : `chat_ai_provider claude` (Claude principal), `chat_claude_primary_failed`
(Claude principal en échec, OpenAI a répondu), `chat_backup_ai_used` et
`trip-planner backup_ai_used` (Claude a servi de secours).
