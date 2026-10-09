"""Page privée /stats-ia : sur quels sujets l'IA n'avait rien de fiable dans son contexte.

Même protection que /stats-partenaires : mot de passe STATS_TOKEN (16 caractères minimum, page absente sinon),
quelques essais seulement, page en « noindex », hors du plan du site. Les chiffres viennent de
services/coverage_log.py : des compteurs par jour et par thème, jamais le texte d'une question.
"""

from __future__ import annotations

import hmac
import os
from html import escape

from flask import Response, abort, request

from routes.monetization import _stats_token
from services.coverage_log import KEEP_DAYS
from services.site_layout import HEAD_ASSETS, site_footer, site_header

_STYLE = """<style>
.cov-wrap{overflow-x:auto}
.cov{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
.cov th,.cov td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;vertical-align:middle}
.cov th:first-child,.cov td:first-child{text-align:left}
.cov tbody th{font-weight:700}
.cov small{display:block;color:var(--muted)}
.cov-bar{display:block;height:6px;margin-top:8px;border-radius:3px;background:var(--accent-soft)}
.cov-bar>span{display:block;height:100%;border-radius:3px;background:var(--accent)}
</style>"""


def _percent(share: float) -> str:
    return f"{round(share * 100)} %"


def _rows(themes: list[dict]) -> str:
    out = []
    for row in themes:
        width = max(0, min(100, round(row["share"] * 100)))
        # Trois colonnes seulement : à 390 px, une quatrième serait coupée. La barre accompagne le sujet et la part
        # non couverte se lit sous le nombre de questions non couvertes.
        out.append(
            f'<tr><th scope="row">{escape(row["label"])}'
            f'<span class="cov-bar" aria-hidden="true"><span style="width:{width}%"></span></span></th>'
            f'<td>{row["questions"]}</td><td>{row["uncovered"]}<small>{_percent(row["share"])}</small></td></tr>'
        )
    return "".join(out)


def ai_providers_status() -> list[str]:
    """Lignes lisibles sur les fournisseurs d'IA : présent ou absent, jamais la valeur d'une clé."""
    from services.backup_ai import backup_enabled, claude_is_primary

    openai_ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    if claude_is_primary():
        principal = "Claude (OpenAI en secours)" if openai_ready else "Claude"
    else:
        principal = "OpenAI" if openai_ready else "aucune clé OpenAI"
    return [
        f"OpenAI : {'clé présente' if openai_ready else 'clé absente'}",
        f"Claude : {'clé présente, il prend le relais si OpenAI ne répond pas' if backup_enabled() else 'clé absente, pas de secours Claude'}",
        f"IA principale : {principal}",
    ]


def render_coverage_page(summary: dict | None, error: str = "") -> str:
    if summary is None:
        body = f"""<h1>Statistiques de l'IA</h1>
<p class="intro">Sujets sur lesquels l'IA manque d'appui. Page privée.</p>
{f'<p class="muted">{escape(error)}</p>' if error else ''}
<form method="post"><label>Mot de passe <input type="password" name="cle" autocomplete="current-password" required></label>
<button class="cta primary" type="submit">Voir les chiffres</button></form>"""
    else:
        days, total, themes = summary["days"], summary["total"], summary["themes"]
        notes = []
        if summary["storage"] != "redis":
            notes.append("Redis n'est pas configuré : les compteurs sont gardés en mémoire, propres à chaque processus du serveur, "
                         "et perdus à chaque redémarrage. Les chiffres ci-dessous sont donc partiels.")
        if total < 50:
            notes.append("Peu de questions comptées pour l'instant : lisez les pourcentages avec prudence.")
        if themes:
            table = (
                '<div class="cov-wrap"><table class="cov"><thead><tr><th scope="col">Sujet</th><th scope="col">Questions</th>'
                '<th scope="col">Non couvertes</th></tr></thead>'
                f"<tbody>{_rows(themes)}</tbody></table></div>"
            )
        else:
            table = '<p class="muted">Aucune question comptée sur cette période.</p>'
        body = f"""<h1>Statistiques de l'IA</h1>
<p class="intro">Pour chaque sujet : combien de questions ont été posées sur les {days} derniers jours, et combien sont
arrivées à l'IA sans rien de fiable dans son contexte. Les sujets en haut de la liste sont ceux à enrichir en premier.</p>
<p>{total} question(s) comptée(s) sur {days} jours. Aucun texte de question n'est conservé : seulement des compteurs par jour
et par sujet, supprimés après {KEEP_DAYS} jours.</p>
{''.join(f'<p class="muted">{escape(note)}</p>' for note in notes)}
{table}
<h2>Fournisseurs d'IA</h2>
<ul>{''.join(f'<li>{escape(line)}</li>' for line in ai_providers_status())}</ul>
<p class="muted">Ces lignes disent seulement si les clés sont présentes sur le serveur ; elles ne les affichent jamais.</p>
<h2>Comment lire ce tableau</h2>
<p><strong>Non couverte</strong> : pour ce sujet, l'IA n'avait reçu ni repère pratique vérifié, ni lieu, plat, fête ou météo de la
base de connaissances, et aucune recherche web n'était déclenchée. Elle répondait alors sans appui de la base de Teranga AI.
Le tri place en premier les sujets qui cumulent le plus de questions non couvertes : ce sont les meilleurs candidats à de
nouveaux repères vérifiés ou à de nouvelles fiches.</p>
<p>Une question qui touche deux sujets est comptée une fois dans chacun : la somme des lignes peut dépasser le nombre de
questions. La ligne <strong>Autre</strong> regroupe les questions qui ne correspondent à aucun sujet connu ; si elle
grossit, il manque un sujet dans la liste.</p>"""
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Statistiques de l'IA | Teranga AI</title><meta name="robots" content="noindex,nofollow">{HEAD_ASSETS}{_STYLE}</head>
<body>{site_header()}<main><article>{body}</article></main>{site_footer()}</body></html>"""


def register_coverage_routes(app, coverage_log, rate_guard=None):
    @app.route("/stats-ia", methods=["GET", "POST"])
    def ai_coverage_stats():
        token = _stats_token()
        if not token:
            abort(404)  # page désactivée tant que STATS_TOKEN n'est pas défini
        headers = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
        if request.method == "GET":
            return Response(render_coverage_page(None), mimetype="text/html", headers=headers)
        if rate_guard is not None and rate_guard("stats_login") is not None:
            return Response(render_coverage_page(None, "Trop d'essais. Réessaie dans quelques minutes."),
                            status=429, mimetype="text/html", headers=headers)
        given = str(request.form.get("cle", ""))
        if not hmac.compare_digest(given.encode("utf-8"), token.encode("utf-8")):
            app.logger.warning("stats-ia: mot de passe refusé")
            return Response(render_coverage_page(None, "Mot de passe incorrect."), status=403, mimetype="text/html", headers=headers)
        return Response(render_coverage_page(coverage_log.summary()), mimetype="text/html", headers=headers)
