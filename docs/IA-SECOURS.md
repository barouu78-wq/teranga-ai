# IA de secours (Claude)

Teranga AI utilise OpenAI. Si OpenAI ne répond pas (panne, surcharge, délai), le chat et le
planificateur demandent automatiquement la réponse à **Claude** (Anthropic). Sans configuration,
rien ne change : le site répond alors avec sa base de connaissances, comme avant.

## Activer

1. Crée un compte sur **console.anthropic.com**, ajoute un moyen de paiement, puis crée une
   clé API (**API Keys** → **Create Key**). Ne l'envoie à personne, ni par message ni par e-mail.
2. Sur **Render** → ton service → **Environment** → **Add Environment Variable** :
   - Key : `ANTHROPIC_API_KEY`
   - Value : colle la clé
3. **Save Changes**. Le site redémarre en une minute.

Optionnel : `ANTHROPIC_MODEL` choisit le modèle (par défaut `claude-sonnet-5-5`).

## Ce qui est couvert

- Chat : réponse écrite complète (sans recherche web ni photos pendant la panne).
- Planificateur : itinéraire complet.
- La voix (dictée, lecture) reste sur OpenAI.

Chaque utilisation est notée dans les journaux Render : `chat_backup_ai_used`,
`trip-planner backup_ai_used`. Tu ne paies Claude que lorsqu'il sert.
