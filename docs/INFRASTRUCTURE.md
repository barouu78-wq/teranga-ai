# Où tourne Teranga AI

État vérifié le **21 octobre 2026** (sources en bas de page). À mettre à jour à chaque changement d'hébergement.

**En une phrase** : le site tourne sur **Render** (un seul service payant, à Francfort) ; le domaine, le DNS et les
e-mails sont chez **OVH** ; le code est sur **GitHub**, et chaque fusion sur `main` est mise en ligne automatiquement.

## Carte

| Élément | Où | Détail |
|---|---|---|
| Site `teranga-ai.fr` et `www` | Render, service `teranga-ai-1` | Offre Starter (0,5 processeur, 512 Mo), Francfort, 1 instance, mise en ligne automatique depuis `main`. Son adresse `onrender.com` est désactivée : tout le trafic passe par teranga-ai.fr. Démarrage `gunicorn app:app`, réglages lus dans `gunicorn.conf.py`. |
| Redis `teranga-redis` | Render Key Value, gratuit, Francfort | Limites de débit, cache des réponses, compteurs. Sans persistance : vidé à chaque redémarrage, sans gravité. La production y est connectée (2 connexions, une par processus Gunicorn). |
| Service `teranga-ai` | Render, gratuit | Copie inutilisée : aucune requête depuis le 14 octobre, mais reconstruite à chaque fusion. À suspendre (décision du 21 octobre). ⚠️ Il est rangé dans le même environnement Render que `teranga-redis`. |
| Domaine `teranga-ai.fr` | OVH | Enregistré, actif. Serveurs DNS `dns111.ovh.net` et `ns111.ovh.net`. |
| E-mails `@teranga-ai.fr` | OVH (e-mails inclus avec le domaine) | Lignes MX, SPF, DKIM et autodiscover complètes. Pas de ligne DMARC. |
| Coolify | Serveur 37.27.40.176, loué hors OVH (hébergeur à lire sur la facture) | Ancienne production, installée début octobre (#157, #201). Ne sert plus teranga-ai.fr depuis le 18 octobre au plus tard. Une copie du site y tournait encore le 21 octobre, à une adresse `sslip.io` en `http`. À arrêter puis résilier (décision du 21 octobre). |
| Code | GitHub `barouu78-wq/teranga-ai` | L'original. Un serveur n'en est qu'une copie. |

## Zone DNS chez OVH (15 lignes au 21 octobre 2026)

| Sous-domaine | Type | Cible | Rôle |
|---|---|---|---|
| `@` | A | `216.24.57.1` | Site (Render). **Une seule** ligne A : deux adresses donnent des erreurs HTTPS (incident du 11 octobre). |
| `www` | CNAME | `teranga-ai-1.onrender.com.` | Site (Render) |
| `@` | NS (×2) | `dns111.ovh.net.`, `ns111.ovh.net.` | DNS chez OVH |
| `@` | MX (×4) | `mx0` (1), `mx1` (5), `mx2` (50), `mx3` (100) `.mail.ovh.net.` | E-mails : ne jamais toucher |
| `@` | SPF | `v=spf1 include:mx.ovh.com ~all` | E-mails : ne jamais toucher |
| `ovhmo-selector-1._domainkey`, `ovhmo-selector-2._domainkey` | CNAME | clés DKIM d'OVH | E-mails : ne jamais toucher |
| `_autodiscover._tcp` | SRV | `0 0 443 zimbra1.mail.ovh.net` | E-mails (réglage automatique des logiciels de messagerie) |
| `@` | TXT | `google-site-verification=…` | Preuve de propriété pour Google Search Console : à garder |
| `coolify` | A | `37.27.40.176` | Ancien Coolify : à supprimer (étape 2 ci-dessous) |
| `ftp` | CNAME | `teranga-ai.fr.` | Reste d'une configuration par défaut, inutile et sans danger |

## Nettoyage décidé le 21 octobre 2026

À faire depuis un ordinateur, **dans cet ordre**. Après chaque étape, vérifier que le site répond.

- [ ] **1. Coolify : arrêter la copie.**
  - Dans *Projects*, vérifier qu'il n'y a rien d'autre que `teranga-ai:main`. S'il y a autre chose (base de données,
    sauvegarde), s'arrêter et le noter ici.
  - Sinon : `teranga-ai:main` → bouton *Running* → **Stop**. Pas *Delete*, pas *Danger Zone*.
- [ ] **2. OVH : supprimer la ligne `coolify`.**
  - Zone DNS → ligne `coolify` A `37.27.40.176` → ⋮ → *Supprimer l'entrée*. **Uniquement celle-là.**
  - Elle se supprime **avant** la résiliation : sinon l'hébergeur peut redonner l'adresse à quelqu'un d'autre, et
    `coolify.teranga-ai.fr` pointerait chez lui.
- [ ] **3. Hébergeur du serveur 37.27.40.176 : résilier.** Rien à sauvegarder : le code est sur GitHub.
- [ ] **4. Render : suspendre le service gratuit.**
  - Service **`teranga-ai`** (adresse `teranga-ai-ev34.onrender.com`, offre *Free*) → *Settings* → tout en bas,
    *Suspend Web Service*.
  - **Surtout pas `teranga-ai-1`** : c'est le site en ligne.
  - Ne jamais supprimer l'environnement ou le projet qui le contient : `teranga-redis` y est rangé et sert à la production.
- [ ] **5. Vérifier.**
  - Le workflow « TLS domain diagnostic » (lecture seule) donne `ok` pour les deux noms.
  - `/health` répond `"status": "ok"` et `"redis": "ok"`.
  - Le service `teranga-ai` apparaît comme suspendu dans Render.

Plus tard, à décider :
- supprimer la ligne `ftp` ;
- ajouter une ligne DMARC (protège contre les faux e-mails envoyés au nom de teranga-ai.fr) ;
- renouveler les clés qui étaient rangées dans les variables de la copie Coolify, une à la fois, en mettant Render à jour.

## Reconstruire de zéro (si Render disparaît)

1. **Service** : créer un service web depuis GitHub `barouu78-wq/teranga-ai`, branche `main`, Python, région Europe.
   - Construction : `pip install -r requirements.txt`.
   - Démarrage : `gunicorn app:app`. Les réglages (2 processus × 4 fils, délai 120 s) viennent de `gunicorn.conf.py`.
   - Sur un hébergeur à conteneurs, utiliser le `Dockerfile`, qui contient les mêmes réglages.
2. **Redis** : créer une base Redis dans la même région et mettre son adresse dans `REDIS_URL`.
3. **Variables** :
   - les noms sont dans `AGENTS.md` (section « Variables d'environnement ») et dans `.env.example` ;
   - leurs valeurs ne sont **jamais** dans le dépôt ;
   - obligatoires : `OPENAI_API_KEY`, `SECRET_KEY` (32 caractères au moins), `TERANGA_ENV=production` ;
   - par défaut, seuls teranga-ai.fr, www et l'adresse Render du service sont acceptés (`app.py`). Un autre
     hébergeur doit être ajouté à `TRUSTED_HOSTS`.
4. **Domaines** :
   - déclarer `teranga-ai.fr` et `www.teranga-ai.fr` chez le nouvel hébergeur ;
   - chez OVH, changer **seulement** la ligne A `@` et le CNAME `www` vers les cibles qu'il donne ;
   - ne jamais toucher aux lignes MX, SPF, DKIM, autodiscover et TXT Google.
5. **Vérifier** :
   - le workflow « TLS domain diagnostic » ;
   - `/health` (avec `"redis": "ok"`) ;
   - `/.well-known/assetlinks.json`, dont dépend l'application Android ;
   - Google Search Console.

### Piège : `render.yaml` ne décrit pas la production

- Il nomme le service `teranga-ai` et demande une machine `2c-8g`, alors que la production est `teranga-ai-1` en
  Starter (0,5 processeur, 512 Mo). Recréer un service avec ce fichier tel quel ferait monter la facture.
- Il n'agit pas sur la production : il a été ajouté le 24 septembre, après la création des deux services (20 septembre),
  et la production n'a jamais pris la taille qu'il demande.
- À corriger dans une PR à part, après avoir vérifié dans Render qu'aucun *Blueprint* ne le suit.
- Sur Render, la commande saisie dans le tableau de bord l'emporte sur `Procfile` et `render.yaml`. C'est pour cela que
  les réglages de Gunicorn sont dans `gunicorn.conf.py`.

## Sources (21 octobre 2026)

- **DNS public et certificats** : workflow « TLS domain diagnostic », exécution 39563782861 (07:41 UTC).
  - `teranga-ai.fr` → `216.24.57.1` ; `www` → `216.24.57.16` et `.18`.
  - Certificats Google Trust Services valides jusqu'au 31 décembre 2026.
- **Render** : API en lecture.
  - Liste des services et de la base Key Value.
  - Requêtes par jour du 14 au 21 octobre.
  - Connexions à Redis.
- **OVH et Coolify** : captures du tableau de bord faites par le propriétaire le 21 octobre (10:04–10:13).
- **Historique** : issue #433 (DNS des 11 et 18 octobre), PR #157 et #201 (Dockerfile pour Coolify).
