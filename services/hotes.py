"""Teranga Hôtes : la page d'une maison d'hôtes et les informations données à l'assistant.

Fiche produit : docs/produit/teranga-hotes.md (« Go hôtes » du propriétaire, 15 novembre 2026).
Une fiche par hébergeur dans data/hotes/<slug>.json, remplie avec les informations que l'hôte a lui-même envoyées.

Règles vérifiées ici :
- aucun établissement réel sans son accord écrit (`accord_ecrit`, date) ; la démonstration est marquée fictive ;
- chaque information garde sa date (`fourni_le`) ;
- jamais de mot de passe ou de code Wi-Fi sur une page publique ;
- l'assistant n'invente rien : ce que l'hôte n'a pas donné se demande à l'accueil.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote

from services.site_layout import HEAD_ASSETS, site_footer

SLUG = re.compile(r"[a-z0-9-]{2,40}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_WHATSAPP = re.compile(r"\+?\d{8,15}")
# Secrets : mot de passe, ou un code donné après un libellé (« Code Wi-Fi : … », « clé : … », « WiFi: … »).
_SECRET = re.compile(r"mot de passe|password|\bmdp\b|\b(?:code|cl[ée])\b[^.:=\n]{0,20}[:=]|\b(?:wi-?fi|ssid|wpa2?)\s*[:=]",
                     re.I)
_WIFI = re.compile(r"wi-?fi", re.I)
_CODE = re.compile(r"\b(?=\w*\d)\w{6,}\b")  # dans un bloc Wi-Fi, un mot de 6 signes ou plus avec un chiffre
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre")

# Icônes au trait, les mêmes que celles de l'accueil (static/home.js, CARD_ICONS).
_S = 'stroke="currentColor" stroke-width="1.7"'
ICONES = {
    "heure": f'<circle cx="12" cy="12" r="9" {_S}/><path d="M12 7v5l3 2" {_S} stroke-linecap="round"/>',
    "repas": f'<path d="M3 12h18a9 9 0 0 1-18 0Z" {_S} stroke-linejoin="round"/>'
             f'<path d="M8 8c0-1.5 1-1.5 1-3M12 8c0-1.5 1-1.5 1-3M16 8c0-1.5 1-1.5 1-3" {_S} stroke-linecap="round"/>',
    "route": f'<circle cx="6" cy="18" r="2.2" {_S}/><path d="M18 9.5s3-3.1 3-5.2a3 3 0 0 0-6 0c0 2.1 3 5.2 3 5.2Z" '
             f'{_S} stroke-linejoin="round"/><path d="M8.2 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7" {_S} '
             'stroke-linecap="round"/>',
    "wifi": f'<path d="M3.5 9.5a13 13 0 0 1 17 0M6.5 13a8.5 8.5 0 0 1 11 0M9.5 16.5a4 4 0 0 1 5 0" {_S} '
            'stroke-linecap="round"/><circle cx="12" cy="19.5" r="1.2" fill="currentColor"/>',
    "boussole": f'<circle cx="12" cy="12" r="9" {_S}/><path d="m15.5 8.5-2.2 4.8-4.8 2.2 2.2-4.8 4.8-2.2Z" {_S} '
                'stroke-linejoin="round"/>',
    "maison": f'<path d="M4 11 12 4l8 7v8a1 1 0 0 1-1 1h-4v-5h-6v5H5a1 1 0 0 1-1-1v-8Z" {_S} stroke-linejoin="round"/>',
    "info": f'<circle cx="12" cy="12" r="9" {_S}/><path d="M12 11v5M12 8h.01" {_S} stroke-linecap="round"/>',
}


class HoteInvalide(ValueError):
    """Fiche d'hébergeur incomplète ou contraire aux règles."""


def _texte(valeur, champ: str, maxi: int, mini: int = 1) -> str:
    if not isinstance(valeur, str) or not mini <= len(valeur.strip()) <= maxi:
        raise HoteInvalide(f"{champ} : texte de {mini} à {maxi} caractères attendu")
    if _SECRET.search(valeur):
        raise HoteInvalide(f"{champ} : pas de mot de passe ni de code sur une page publique")
    return valeur.strip()


def _date(valeur, champ: str) -> str:
    if not isinstance(valeur, str) or not _DATE.fullmatch(valeur):
        raise HoteInvalide(f"{champ} : date AAAA-MM-JJ attendue")
    _dt.date.fromisoformat(valeur)
    return valeur


def valider_hote(data: dict) -> dict:
    """Vérifie une fiche et renvoie sa version propre ; lève HoteInvalide sinon."""
    if not isinstance(data, dict):
        raise HoteInvalide("fiche : objet attendu")
    slug = data.get("slug")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise HoteInvalide("slug : minuscules, chiffres et tirets (2 à 40)")
    demo = data.get("demo")
    if not isinstance(demo, bool):
        raise HoteInvalide("demo : vrai ou faux")
    accord = data.get("accord_ecrit", "")
    if accord:
        _date(accord, "accord_ecrit")
    elif not demo:
        raise HoteInvalide("accord_ecrit : un établissement réel n'apparaît qu'avec son accord écrit (date)")
    infos = data.get("infos")
    if not isinstance(infos, list) or not 1 <= len(infos) <= 12:
        raise HoteInvalide("infos : de 1 à 12 blocs")
    propres = []
    for info in infos:
        if not isinstance(info, dict):
            raise HoteInvalide("infos : objets attendus")
        icone = info.get("icone", "info")
        if icone not in ICONES:
            raise HoteInvalide(f"icone : une de {sorted(ICONES)}")
        bloc = {"icone": icone, "titre": _texte(info.get("titre"), "titre", 40),
                "valeur": _texte(info.get("valeur"), "valeur", 120)}
        if info.get("detail"):
            bloc["detail"] = _texte(info["detail"], "detail", 120)
        if (icone == "wifi" or _WIFI.search(bloc["titre"])) and any(
                _CODE.search(bloc.get(champ, "")) for champ in ("valeur", "detail")):
            raise HoteInvalide("Wi-Fi : pas de code sur une page publique (écrire « Code à l’accueil »)")
        propres.append(bloc)
    questions = data.get("questions", [])
    if not isinstance(questions, list) or len(questions) > 4:
        raise HoteInvalide("questions : 4 au plus")
    whatsapp = data.get("whatsapp", "")
    if whatsapp and (not isinstance(whatsapp, str) or not _WHATSAPP.fullmatch(whatsapp)):
        raise HoteInvalide("whatsapp : chiffres seulement, avec l'indicatif (ex. +221771234567)")
    indexer = data.get("indexer", False)
    if not isinstance(indexer, bool):
        raise HoteInvalide("indexer : vrai ou faux")
    return {
        "slug": slug, "demo": demo, "accord_ecrit": accord, "indexer": indexer,
        "nom": _texte(data.get("nom"), "nom", 80, 2), "ville": _texte(data.get("ville"), "ville", 60),
        "region": _texte(data["region"], "region", 60) if data.get("region") else "",
        "accroche": _texte(data["accroche"], "accroche", 200) if data.get("accroche") else "",
        "fourni_le": _date(data.get("fourni_le"), "fourni_le"),
        "infos": propres, "questions": [_texte(q, "question", 80) for q in questions], "whatsapp": whatsapp,
    }


def charger_hotes(dossier: Path) -> dict[str, dict]:
    """Toutes les fiches du dossier, par slug ; une fiche invalide arrête le démarrage (et le CI)."""
    hotes = {}
    for fichier in sorted(Path(dossier).glob("*.json")):
        hote = valider_hote(json.loads(fichier.read_text(encoding="utf-8")))
        if hote["slug"] != fichier.stem:
            raise HoteInvalide(f"{fichier.name} : le slug doit être le nom du fichier")
        hotes[hote["slug"]] = hote
    return hotes


def date_longue(iso: str) -> str:
    jour = _dt.date.fromisoformat(iso)
    return f"{jour.day} {MOIS[jour.month - 1]} {jour.year}"


def _simple(texte: str) -> str:
    return texte.replace(" ", " ").replace(" ", " ")


def contexte_hote(hote: dict) -> str:
    """Bloc ajouté aux instructions de l'IA quand la question vient de la page d'un hébergeur."""
    lieu = hote["ville"] + (f" ({hote['region']})" if hote["region"] else "")
    lignes = [f"INFORMATIONS DE L'ÉTABLISSEMENT (fournies par l'hôte le {_simple(date_longue(hote['fourni_le']))}) "
              f"— {hote['nom']}, {lieu}."]
    if hote["demo"]:
        lignes.append("C'est un établissement fictif, pour la démonstration : si on te demande s'il existe, dis-le.")
    for info in hote["infos"]:
        detail = f" ({info['detail']})" if info.get("detail") else ""
        lignes.append(f"- {info['titre']} : {info['valeur']}{detail}")
    lignes.append(
        "Règles : pour toute question sur l'établissement (horaires, services, chambres, prix, réservations), "
        "réponds seulement avec ces informations et précise « information de l'établissement ». Si l'information "
        "n'y est pas, dis de la demander à l'accueil, sans rien inventer (ni prix, ni disponibilité). Pour le reste "
        "(le Sénégal, les démarches, les lieux), réponds comme d'habitude."
    )
    return _simple("\n".join(lignes))


def _icone(nom: str) -> str:
    return f'<svg class="hote-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">{ICONES[nom]}</svg>'


def _lien_question(slug: str, question: str) -> str:
    return f"/?hote={slug}&amp;q={escape(quote(question))}"


def page_hote(hote: dict) -> str:
    """Page publique d'un hébergeur (téléphone d'abord), sans script : le formulaire marche sans JavaScript."""
    slug, nom = hote["slug"], escape(hote["nom"])
    lieu = escape(hote["ville"] + (f" · {hote['region']}" if hote["region"] else ""))
    robots = "index,follow" if hote["indexer"] else "noindex,nofollow"
    badge = '<span class="hote-demo">Exemple · établissement fictif</span>' if hote["demo"] else ""
    accroche = f'<p class="hote-accroche">{escape(hote["accroche"])}</p>' if hote["accroche"] else ""
    questions = "".join(
        f'<a class="hote-chip" href="{_lien_question(slug, q)}">{escape(q)}</a>' for q in hote["questions"]
    )
    cartes = "".join(
        f'<div class="hote-card{" full" if len(info["valeur"]) > 28 else ""}">{_icone(info["icone"])}'
        f'<small>{escape(info["titre"])}</small><strong>{escape(info["valeur"])}</strong>'
        + (f'<em>{escape(info["detail"])}</em>' if info.get("detail") else "") + "</div>"
        for info in hote["infos"]
    )
    contact = (
        f'<a class="hote-contact" href="https://wa.me/{hote["whatsapp"].lstrip("+")}" rel="noopener">'
        "Écrire à l’accueil sur WhatsApp</a>" if hote["whatsapp"] else ""
    )
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="{robots}"><title>{nom} · Teranga AI</title>'
        f'<meta name="description" content="{nom} : l’essentiel du séjour et un assistant pour tes questions.">'
        f"{HEAD_ASSETS}</head><body class=\"hote\">"
        f'<header class="hote-top"><a class="hote-brand" href="/">Teranga AI</a>{badge}</header>'
        f'<main><section class="hote-hero"><p class="hote-lieu">{lieu}</p><p class="kicker">Bienvenue</p>'
        f"<h1>{nom}</h1>{accroche}</section>"
        '<form class="hote-ask" action="/" method="get" role="search">'
        f'<input type="hidden" name="hote" value="{slug}">'
        '<label class="sr-only" for="hote-q">Ta question sur ton séjour</label>'
        '<input id="hote-q" name="q" type="text" maxlength="300" placeholder="Pose ta question sur ton séjour…" '
        'autocomplete="off" enterkeyhint="send">'
        '<button type="submit" aria-label="Envoyer la question"><svg viewBox="0 0 24 24" fill="none" '
        'aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg></button></form>'
        f'<nav class="hote-chips" aria-label="Questions fréquentes">{questions}</nav>'
        f'<h2>L’essentiel</h2><div class="hote-grid">{cartes}</div>'
        f'<p class="hote-src">Informations de l’établissement, fournies par l’hôte le {date_longue(hote["fourni_le"])}.</p>'
        f"{contact}"
        '<h2>Aussi utile</h2><nav class="hote-links" aria-label="Pages utiles">'
        '<a href="/urgences">Urgences</a><a href="/lieux">Lieux à visiter</a>'
        '<a href="/calendrier-fetes-senegal">Fêtes et jours fériés</a></nav>'
        '<p class="hote-note">Assistant fourni par <span translate="no">Teranga AI</span>. Les informations de la '
        "maison viennent de l’hôte ; les autres réponses viennent de la base vérifiée de Teranga.</p>"
        f"</main>{site_footer()}</body></html>"
    )


def qr_svg(url: str) -> bytes:
    """QR code de la page, en SVG (à imprimer pour les chambres)."""
    import segno

    tampon = io.BytesIO()
    segno.make(url, error="m").save(tampon, kind="svg", scale=8, border=4, dark="#14110d", xmldecl=True)
    return tampon.getvalue()
