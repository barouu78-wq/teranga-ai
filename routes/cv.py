"""Mon CV (Teranga Emploi, étape 1) : la page /cv et /api/cv, qui fait créer le CV par Claude.

Rien n'est gardé : ni le fichier, ni le récit, ni l'offre, ni le CV rendu (pas de cache, journaux sans contenu).
"""

from flask import Response, jsonify, request

from services.backup_ai import backup_enabled, claude_response
from services.cv import CONSIGNE_CV, ERREURS_DEMANDE, CvIllisible, DemandeInvalide, construire_demande, lire_reponse, page_cv
from services.fichiers import FichierInvalide, message_erreur

NO_STORE = {"Cache-Control": "no-store"}


def register_cv_routes(app, site_url, *, require_json_post, rate_guard, logger):
    @app.get("/cv")
    def cv_page():
        return Response(page_cv(site_url), mimetype="text/html", headers={"Cache-Control": "public, max-age=600"})

    @app.post("/api/cv")
    @require_json_post
    def cv_api():
        refus = rate_guard("cv")  # quotas par minute et par heure, et plafond d'IA du jour (AI_BUDGET_BUCKETS)
        if refus:
            return refus
        if not backup_enabled():
            # Le CV (photo, PDF) n'est lu que par Claude : sans lui, le dire plutôt qu'un CV fait sans l'avoir lu.
            return jsonify({"error": "La création de CV n'est pas disponible pour l'instant. Réessaie plus tard."}), 503, NO_STORE
        try:
            prompt, bloc = construire_demande(request.get_json(silent=True) or {})
        except FichierInvalide as exc:
            return jsonify({"error": message_erreur(exc.code)}), 400, NO_STORE
        except DemandeInvalide as exc:
            return jsonify({"error": ERREURS_DEMANDE[exc.code]}), 400, NO_STORE
        try:
            final = claude_response(prompt, system=CONSIGNE_CV, max_tokens=4000, timeout=60.0, attachment=bloc)
            cv = lire_reponse(getattr(final, "output_text", "") or "")
        except CvIllisible:
            logger.warning("cv_reponse_illisible")
            return jsonify({"error": "Le CV n'a pas pu être créé. Réessaie dans un moment."}), 502, NO_STORE
        except Exception as exc:  # noqa: BLE001 - jamais de trace : elle pourrait contenir des données du CV
            logger.warning("cv_claude_echec %s", type(exc).__name__)
            return jsonify({"error": "Le CV n'a pas pu être créé. Réessaie dans un moment."}), 502, NO_STORE
        logger.info("cv_cree fichier=%s offre=%s lettre=%s", bool(bloc) or "[Texte du document Word" in prompt,
                    "[Offre d'emploi" in prompt, bool(cv["lettre"]))
        return jsonify({"cv": cv}), 200, NO_STORE
