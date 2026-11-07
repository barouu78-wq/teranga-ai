# Liens marqués : savoir d'où viennent les visiteurs

Depuis la V5, une visite qui arrive par un **lien marqué** est comptée par réseau. Le comptage se fait sur le site
lui-même : pas d'outil de suivi extérieur, aucune donnée personnelle (ni adresse IP, ni identifiant). Les chiffres
sont sur la page privée **`/stats-partenaires`** (mot de passe `STATS_TOKEN`), ligne « Visites venues des réseaux ».

## Les liens à utiliser

| Où tu publies | Lien à mettre |
|---|---|
| TikTok (bio et vidéos) | `https://teranga-ai.fr/?utm_source=tiktok` |
| Instagram (bio, stories, Reels) | `https://teranga-ai.fr/?utm_source=instagram` |
| WhatsApp (statut, chaîne, groupes) | `https://teranga-ai.fr/?utm_source=whatsapp` |
| Facebook | `https://teranga-ai.fr/?utm_source=facebook` |
| YouTube (description, Shorts) | `https://teranga-ai.fr/?utm_source=youtube` |

Pour une page précise, la marque se met de la même façon : `https://teranga-ai.fr/joj-dakar-2026?utm_source=tiktok`.

## À savoir

- **À faire une fois :** remplacer le lien de la bio TikTok et Instagram par le lien marqué ci-dessus.
- Seuls ces cinq réseaux sont comptés ; une autre valeur est ignorée (pas de ligne inventée).
- Seules les visites faites dans un vrai navigateur comptent (Safari, Chrome, Firefox, ou le navigateur intégré de
  TikTok et Instagram). Les aperçus de liens (le petit encadré que WhatsApp ou Facebook fabriquent) et les outils
  automatiques ne comptent pas.
- Un même visiteur ne peut pas gonfler les chiffres : au plus 6 visites comptées par minute et 60 par heure.
- Le lien sans marque (`https://teranga-ai.fr`) marche toujours, mais sa visite n'est attribuée à aucun réseau.
- Sur TikTok, le lien écrit dans la légende d'une vidéo n'est en général pas cliquable : c'est le lien de la bio qui compte.
