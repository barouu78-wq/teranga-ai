# Mesurer où le temps passe dans une réponse du chat

Chaque requête vers `/chat`, `/stt` et `/tts` écrit **une ligne de journal** `latence route=…`, faite
uniquement de nombres et d'étiquettes fixes. Elle sert à **mesurer avant d'optimiser** : rien n'a été
accéléré par ce changement, et aucune question, réponse, adresse IP ou clé n'y figure.

> **Aucun objectif chiffré n'est fixé ici.** L'objectif (« une réponse en moins de … secondes ») se fixe
> **après la première mesure réelle**, sur de vraies lignes de la production, jamais avant.

## À quoi ressemble une ligne

```text
latence route=chat total_ms=2310.4 contexte_ms=12.8 recherche_ms=- premier_mot_ms=1480.2 fournisseur_ms=1410.9 cache=non web=non modele=gpt-5.6-luna mode=flux statut=ok
latence route=stt total_ms=950.1 fournisseur_ms=902.6 modele=gpt-4o-transcribe statut=ok
```

(Chiffres inventés pour montrer la forme : ce ne sont pas des mesures.)

| Champ | Sens |
|---|---|
| `route` | `chat`, `stt` ou `tts` |
| `total_ms` | durée de la requête dans l'application, jusqu'à la **fin** de la réponse (pour le chat en flux : le dernier octet envoyé, ou la fermeture par le visiteur) |
| `contexte_ms` | préparation du contexte de l'IA : `parse_chat_payload` et tout son assemblage (base de connaissances, repères pratiques, calendrier, partenaires, **météo en direct** si la question en demande) |
| `recherche_ms` | temps passé dans le connecteur de recherche externe (Tavily, Exa, Firecrawl) quand il est appelé ; `-` s'il ne l'est pas. Proche de `0.0` si aucune clé de recherche n'est configurée |
| `premier_mot_ms` | du début de la requête au **premier texte envoyé au visiteur**. `-` en mode JSON et si rien n'a été écrit |
| `fournisseur_ms` | attente du fournisseur d'IA : de l'envoi de la requête au modèle jusqu'au premier mot (en mode JSON : tout l'appel). Pour `/stt` et `/tts` : la durée de l'appel au fournisseur de voix |
| `cache` | `oui` si la réponse vient du cache des réponses (aucun modèle appelé), `non` sinon, `-` pour les demandes de photos seules et les requêtes refusées avant |
| `web` | `oui` si le modèle a reçu l'**outil de recherche web du fournisseur**. Son temps est **dans** `fournisseur_ms` (il ne se sépare pas) ; la recherche externe de `recherche_ms` le remplace quand elle réussit |
| `modele` | nom du modèle réellement appelé (lu dans la configuration), `-` s'il n'y en a pas (cache, photos, requête refusée) |
| `mode` | `flux` (le site) ou `json` (reprise du site quand le flux n'a donné aucun texte) |
| `statut` | `ok`, `secours` (l'IA a échoué, réponse de repli), `erreur`, `abandon` (le visiteur a fermé avant la fin), `refuse` (limite de débit, HTTP 429), `invalide` (requête refusée, 4xx) |

Les lignes `/stt` et `/tts` n'ont que `total_ms`, `fournisseur_ms`, `modele` et `statut`.

Un nombre se lit en millisecondes avec une décimale. `-` veut dire « sans objet » : ce n'est pas zéro et le
script l'ignore.

### Ce que ces lignes ne disent pas

- Le chronomètre démarre quand la route reçoit la requête. Il **n'inclut pas** l'attente dans la file de
  Gunicorn, le réseau du visiteur ni les contrôles de type de contenu, d'origine et CSRF de `/chat` et `/tts`, qui répondent avant ;
  ces requêtes refusées ne laissent pas de ligne (`/stt` fait ces contrôles dans la route : ils laissent
  une ligne `invalide`).
- L'attente des images et de la carte, lancées pendant que le modèle écrit, compte dans `total_ms` sans
  colonne à part.
- Ce qui reste de `premier_mot_ms` une fois `contexte_ms`, `recherche_ms` et `fournisseur_ms` retirés
  (les `-` comptent pour 0) est le travail d'avant l'appel au modèle : limites de débit (Redis), comptage
  anonyme des sujets, recherche dans le cache des réponses.
- Une réponse de repli (`secours`) peut avoir appelé un second fournisseur (Claude) ou la base de
  connaissances : son temps est dans `premier_mot_ms` et `total_ms`.

## Lire ces lignes dans les journaux Render

Les lignes sont écrites sur la sortie standard, donc visibles dans les journaux du service (onglet
**Logs** de Render, champ de recherche) comme avec le connecteur Render en lecture seule. Leur début est
toujours `latence route=` : c'est ce texte qu'il faut filtrer.

Avec le connecteur Render (`list_logs`), le filtre `text` accepte du texte, des jokers et des expressions
régulières. Exemples de paramètres :

| But | `text` |
|---|---|
| toutes les lignes | `latence route=` |
| le chat seulement | `latence route=chat` |
| la voix | `latence route=stt` puis `latence route=tts` |
| les erreurs du chat | `latence route=chat .*statut=erreur` |
| les réponses du cache | `latence route=chat .*cache=oui` |

Autres paramètres utiles : `resource` (l'identifiant du service), `type` = `app` (journaux de
l'application, pas les journaux de requêtes HTTP), `startTime` et `endTime`, `limit` = 100 au maximum par
appel. Quand la réponse indique qu'il reste des lignes (`hasMore`), recommencer avec les horodatages
`nextStartTime` et `nextEndTime` qu'elle donne. Le connecteur ne remonte pas au-delà de 30 jours.
À environ 300 requêtes par jour, une journée tient en quelques pages.

Si un filtre par expression régulière ne renvoie rien, prendre le filtre simple (`latence route=chat`) et
trier ensuite avec `--garder` du script ci-dessous : c'est plus lent mais ça ne dépend pas de la syntaxe du
filtre. (La syntaxe des expressions régulières du connecteur est à vérifier au premier essai.)

Pour obtenir un export : copier les lignes de la page Logs de Render, ou demander au connecteur de les
lister, puis les coller dans un fichier texte. Un horodatage ou un préfixe devant `latence` ne gêne pas.
Ne collez pas deux fois la même période : chaque ligne comptée deux fois fausserait les médianes.

## Calculer médiane et p95 avec le script

```bash
python scripts/lire_latence.py < export.txt
python scripts/lire_latence.py --tout < export.txt                   # garde aussi secours, erreurs, abandons…
python scripts/lire_latence.py --garder mode=flux --garder web=oui < export.txt
```

Le script lit l'entrée standard (collée dans un terminal avec Ctrl+D à la fin, ou redirigée), ignore ce qui
n'est pas une ligne `latence`, et affiche par route : le nombre de requêtes, la médiane et le p95 de chaque
durée. Le chat est séparé selon `cache=oui` / `cache=non` : une réponse du cache ne doit pas se mêler aux
appels au modèle. Par défaut seules les requêtes `ok` comptent dans les médianes (le nombre de chaque
statut reste affiché), pour qu'une erreur rapide ne fasse pas croire que tout va vite.

Exemple. Entrée (chiffres **fictifs**, pour montrer le calcul) :

```latence-entree
latence route=chat total_ms=2100.0 contexte_ms=14.2 recherche_ms=- premier_mot_ms=1450.3 fournisseur_ms=1390.1 cache=non web=non modele=gpt-5.6-luna mode=flux statut=ok
latence route=chat total_ms=1800.5 contexte_ms=11.0 recherche_ms=- premier_mot_ms=1210.0 fournisseur_ms=1160.4 cache=non web=non modele=gpt-5.6-luna mode=flux statut=ok
latence route=chat total_ms=3400.2 contexte_ms=19.7 recherche_ms=- premier_mot_ms=2500.8 fournisseur_ms=2440.0 cache=non web=oui modele=gpt-5.6-luna mode=flux statut=ok
latence route=chat total_ms=2600.0 contexte_ms=12.5 recherche_ms=- premier_mot_ms=1800.0 fournisseur_ms=1750.2 cache=non web=non modele=gpt-5.6-luna mode=flux statut=ok
latence route=chat total_ms=9800.0 contexte_ms=15.3 recherche_ms=- premier_mot_ms=8100.6 fournisseur_ms=8040.9 cache=non web=oui modele=gpt-5.6-sol mode=flux statut=ok
latence route=chat total_ms=700.0 contexte_ms=13.0 recherche_ms=- premier_mot_ms=- fournisseur_ms=640.0 cache=non web=non modele=gpt-5.6-luna mode=flux statut=erreur
latence route=chat total_ms=35.0 contexte_ms=9.0 recherche_ms=- premier_mot_ms=8.0 fournisseur_ms=- cache=oui web=non modele=- mode=flux statut=ok
latence route=tts total_ms=900.0 fournisseur_ms=870.0 modele=gpt-4o-mini-tts statut=ok
```

Sortie :

```latence-sortie
Lignes « latence » lues : 8
Statuts gardés : ok seulement (--tout pour tout garder)

chat, cache=non : 5 requête(s) gardée(s) sur 6 (erreur=1, ok=5)
  total_ms        n=5     médiane=2600.0     p95=9800.0
  contexte_ms     n=5     médiane=14.2       p95=19.7
  premier_mot_ms  n=5     médiane=1800.0     p95=8100.6
  fournisseur_ms  n=5     médiane=1750.2     p95=8040.9
  Attention : moins de 20 requêtes, le p95 est peu fiable.

chat, cache=oui : 1 requête(s) gardée(s) sur 1 (ok=1)
  total_ms        n=1     médiane=35.0       p95=35.0
  contexte_ms     n=1     médiane=9.0        p95=9.0
  premier_mot_ms  n=1     médiane=8.0        p95=8.0
  Attention : moins de 20 requêtes, le p95 est peu fiable.

tts : 1 requête(s) gardée(s) sur 1 (ok=1)
  total_ms        n=1     médiane=900.0      p95=900.0
  fournisseur_ms  n=1     médiane=870.0      p95=870.0
  Attention : moins de 20 requêtes, le p95 est peu fiable.
```

## Les mêmes calculs à la main

Pour une durée (par exemple `total_ms`) d'un même groupe (même route, même `cache`, statut `ok`) :

1. Garder les valeurs numériques (ignorer les `-`) et les **trier** de la plus petite à la plus grande.
   Soit `n` leur nombre.
2. **Médiane** : la valeur du milieu si `n` est impair (rang `(n+1)/2`) ; la moyenne des deux valeurs du
   milieu (rangs `n/2` et `n/2 + 1`) si `n` est pair.
3. **p95** (méthode du « rang le plus proche ») : calculer `rang = 0,95 × n`, l'**arrondir vers le haut**,
   et prendre la valeur de ce rang dans la liste triée.

Dans l'exemple, `total_ms` du chat sans cache : `1800.5, 2100.0, 2600.0, 3400.2, 9800.0` (`n = 5`).
Médiane : rang 3, soit `2600.0`. p95 : `0,95 × 5 = 4,75`, arrondi à 5, soit la 5e valeur `9800.0`.
Avec peu de requêtes le p95 est simplement la plus lente : il ne devient parlant qu'à partir d'une vingtaine
de requêtes par groupe (le script le rappelle). Avec `n = 20`, le p95 est la 19e valeur ; avec `n = 100`,
la 95e.

Un tableur fait de même : trier la colonne, puis `MEDIAN(plage)` et `PERCENTILE.INC(plage; 0,95)` donnent
des valeurs voisines (le tableur interpole entre deux valeurs, le script prend une valeur réellement
observée : de petites différences sont normales).

## Lire un résultat

- `premier_mot_ms` est ce que le visiteur ressent avant que le texte apparaisse ; `total_ms − premier_mot_ms`
  est la durée d'écriture de la réponse.
- Comparer `fournisseur_ms` et `premier_mot_ms` : si `fournisseur_ms` en représente presque tout, le temps
  est chez le fournisseur ; sinon il est chez nous (`contexte_ms`, `recherche_ms`, ou le travail d'avant
  l'appel décrit plus haut).
- Séparer les cas avec `--garder` : `web=oui` / `web=non`, `modele=…`, `cache=…`, `mode=…`.
- Attendre quelques jours pour que chaque groupe dépasse une vingtaine de lignes avant de comparer des p95.
- **Fixer un objectif seulement ensuite**, en notant la date et le nombre de requêtes de la mesure de départ.

## Pourquoi un journal à part

Le journal de l'application (`app.logger`) reste au niveau WARNING sous Gunicorn : constaté en lançant
Gunicorn avec les options du `Procfile`, les lignes de niveau INFO (`http_request`, `chat_ttfb_ms`…)
n'apparaissent pas ; seuls les journaux d'accès de Gunicorn sortent. Les lignes de latence passent donc par
un journal dédié (`teranga.latence`), réglé sur INFO, qui écrit sur la sortie standard, sans toucher à la
configuration du reste de l'application. Les anciennes lignes `chat_*_ms` restent en place, inchangées.

## Confidentialité

Une ligne est construite **uniquement** à partir de nombres et de valeurs fixes (route, `oui`/`non`, mode,
statut) ou validées (nom du modèle, lu dans la configuration : lettres, chiffres et `. _ : -`, 48 caractères
au plus, sinon `autre`). Toute autre valeur devient `-`. Ni le texte de la question ou de la réponse, ni le
texte transcrit ou lu à voix haute, ni l'adresse IP, ni l'identifiant du visiteur, ni une clé, ni un
message d'erreur du fournisseur n'entrent dans la ligne. `tests/test_latence_confidentialite.py` le
vérifie sur la vraie application et échoue si un texte de test y apparaît.

## Côté navigateur : le banc simulé de la voix

Les lignes `latence` mesurent le serveur. En conversation vocale, l'attente que la personne ressent commence plus
tôt : quand elle a fini de parler. Le test `tests/e2e/test_voice_latency.py` découpe ce trajet dans Chromium, avec de
**faux** fournisseurs auxquels on impose un retard fixe. Ses chiffres sont **simulés** : ils ne disent rien du temps
réel d'OpenAI ni d'un téléphone. Ils servent à repérer une régression du site, jamais à annoncer un temps de réponse.

| Étape, dans l'ordre | Ce qu'elle attend | Où |
|---|---|---|
| 1. Silence | 720 ms sans voix (`VOICE_SILENCE_MS`), contrôlés toutes les 55 ms, puis l'arrêt de l'enregistreur : environ 800 ms | `static/home.js` |
| 2. Transcription | l'envoi de l'audio à `/stt` et le fournisseur (ligne `route=stt`) | `routes/stt.py` |
| 3. Passage `/stt` → `/chat` | le travail de la page : quelques ms (environ 40 ms navigateur ralenti 12 fois) | `static/home.js` |
| 4. Réponse du chat | le premier jeton, puis une première partie complète d'au moins 60 caractères lus (`VOICE_FIRST_MIN`) (ligne `route=chat`) | `routes/chat.py` |
| 5. Attente de la première partie | 700 ms (`VOICE_FIRST_WAIT_MS`) quand la réponse semble courte (moins de 240 caractères reçus), pour qu'une réponse courte reste en un seul appel à `/tts` ; aucune attente sinon | `templates/home.html` |
| 6. Voix | la demande à `/tts` et le fournisseur (ligne `route=tts`) | `routes/tts.py` |
| 7. Démarrage du son | le fichier reçu, le lecteur monté, `play()` : environ 5 ms (environ 100 ms navigateur ralenti 12 fois) | `templates/home.html` |

```bash
E2E_REQUIRED=1 pytest -q tests/e2e/test_voice_latency.py -s                          # le détail de chaque tour
E2E_CPU_THROTTLE=12 E2E_REQUIRED=1 pytest -q tests/e2e/test_voice_latency.py -s      # navigateur ralenti 12 fois
```

Les seuils du test sont des **garde-fous de non-régression** du banc, larges exprès (le test doit passer aussi sur une
machine chargée), pas des objectifs. Comme pour le serveur, l'objectif se fixe après une mesure réelle.
