---
name: audit-seo
description: Auditer le SEO de toutes les pages du sitemap de Teranga AI (titre, description, canonique, aperçu de partage, JSON-LD, doublons) et corriger les défauts. À utiliser après l'ajout ou la modification d'une page, avant une PR touchant le HTML, ou quand le propriétaire demande un contrôle SEO.
---

# Audit SEO

## Lancer l'audit
```bash
python scripts/audit_seo.py          # 0 = tout est conforme, 1 = au moins un problème
python scripts/audit_seo.py --json   # même chose, lisible par un script
```
Il parcourt les ~200 pages du `/sitemap.xml` avec le client de test Flask : **aucun réseau**, il juge le code
tel qu'il sera déployé. Il ne dit rien de la production (redirections, vitesse, indexation Google).

## Ce qui est vérifié, page par page
Titre ≤ 65 caractères · description de 70 à 165 · URL canonique égale à l'adresse du sitemap · un seul `<h1>` ·
`og:title`, `og:description`, `og:url`, `og:image`, `og:type` · `twitter:card` · JSON-LD valide · `lang` · viewport ·
pas de `noindex` · pas d'image sans `alt` · pas de titre ni de description en double entre pages.

## Corriger selon le problème
- **Aperçu de partage manquant** : utiliser `social_meta(titre, description, url, site_url)` de
  `services/site_layout.py` (ne pas recopier les balises à la main).
- **Titre / description** : la longueur se compte sans les entités HTML (`&#x27;` = une apostrophe).
  Pages du catalogue : `SEO_PAGES` dans `services/seo.py` ; lieux : `place_title` et `place_description`
  dans `services/places.py`.
- **Canonique** : `site_url.rstrip('/') + chemin`, jamais l'adresse `onrender.com`.
- **Nouvelle page** : l'ajouter au sitemap (`routes/seo.py`) **et** vérifier qu'elle passe l'audit.

## Garde-fous
Les tests `tests/test_seo_quality.py` et `tests/test_audit_seo_script.py` rejouent l'essentiel dans le CI.
Ne jamais assouplir une limite (65 / 70-165) pour faire passer une page : raccourcir le texte.
Le propriétaire doit encore, de son côté, envoyer `https://teranga-ai.fr/sitemap.xml` dans Search Console
(propriété `teranga-ai.fr`) et demander l'indexation des pages principales.
