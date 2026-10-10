# Claude : IA de secours ou IA principale

Teranga AI utilise OpenAI. Avec une clé Anthropic, **Claude** peut :

- **servir de secours** (réglage par défaut) : si OpenAI ne répond pas (panne, surcharge, délai),
  le chat et le planificateur demandent automatiquement la réponse à Claude ;
- **devenir l'IA principale** : Claude répond à tout, avec sa propre recherche web, et OpenAI
  devient le secours.

Sans clé, rien ne change : le site répond avec OpenAI, puis avec sa base vérifiée (voir « Mode
autonome » plus bas).

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

## Mode autonome : quand aucune IA ne répond

Chaîne de repli du chat, dans l'ordre :

1. **OpenAI** (ou Claude si `AI_PRINCIPALE=claude`) ;
2. **l'autre IA**, si la clé `ANTHROPIC_API_KEY` existe (Claude, ou OpenAI quand Claude est principal) ;
3. **la base vérifiée du site** (`services/fallback_answer.py`) : aucun appel externe, donc elle répond
   même si les deux IA sont en panne ou sans crédit.

Dans ce troisième cas, le site annonce que l'assistant est « momentanément indisponible » puis donne
ce qu'il sait, **repris tel quel** (aucune reformulation, aucun fait ajouté) :

- le **lieu ou le plat** cité dans la question (fiche de la base) ;
- les **repères pratiques vérifiés** qui correspondent : urgences, santé, premiers secours, argent,
  arnaques, mobile money, visa, papiers, factures d'électricité, protection sociale, études,
  transports, SIM, foncier… Au plus **3 sujets** et environ 3 000 caractères ; un repère n'est
  jamais coupé. Pour un sujet long (premiers secours, arnaques, papiers), seuls les repères qui
  répondent à la question sont gardés ; les premiers secours gardent toujours leur cadre de
  précautions (SAMU 1515) ;
- les **prochaines fêtes** (3 au plus) quand la question en parle ; les dates lunaires restent
  marquées « estimée, à confirmer » ;
- une **urgence** que les sujets ne couvrent pas (incendie, noyade, crise cardiaque…) reçoit les
  numéros d'urgence (Police 17, pompiers 18, SAMU 1515) et les pages utiles, jamais une erreur sèche.

Quand rien ne correspond, le site préfère **ne rien inventer** : le message honnête (« pas de réponse
prête ») renvoie vers `/lieux`, `/urgences`, `/calendrier-fetes-senegal` et `/trip-planner`, et ne
rappelle les numéros d'urgence que si la question touche à une urgence. Il est prêt dans
`knowledge_fallback(..., always=True)`, mais le chat ne l'utilise pas encore : en attendant, une
question sans rapport avec la base reçoit toujours le message d'erreur habituel.

Pour le développeur : un nouveau sujet de repères pratiques reçoit son titre dans `_TITLES`
(`services/fallback_answer.py`) ; sans titre, il s'affiche sous « Repères pratiques ».

Journaux Render : `chat_fallback_used mode=stream` ou `mode=json` quand la base du site a répondu.

## Ce qui est couvert

- Chat : réponse écrite complète. Les photos et la carte viennent d'autres services et restent
  les mêmes quelle que soit l'IA.
- Planificateur : itinéraire complet. Il passe sur l'autre IA si la clé existe, mais n'a **pas** de repli
  sur la base du site (un itinéraire demande une IA) : si aucune IA ne répond, il affiche son message
  d'erreur.
- La voix (dictée, lecture) reste toujours sur OpenAI.

Journaux Render : `chat_ai_provider claude` (Claude principal), `chat_claude_primary_failed`
(Claude principal en échec, OpenAI a répondu), `chat_backup_ai_used` et
`trip-planner backup_ai_used` (Claude a servi de secours).
