"""Profil « Tout le Sénégal » (general), par défaut : Teranga répond à toute question sur le Sénégal.

Demande du propriétaire (24 octobre 2026) : « une IA qui peut répondre à tout type de question sur le Sénégal », pour
toute la population, et qui reste une IA. Avant, un nouveau visiteur était rangé d'office dans le profil « touriste » :
l'IA recevait la consigne de privilégier le voyage, même pour un habitant qui demandait ses papiers. Les quatre profils
(touriste, résident, diaspora, commerçant) restent au choix ; seul le profil par défaut change.
"""

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.chat_payload_service import _AUDIENCE_INSTRUCTIONS  # noqa: E402
from services.practical_facts import matching_topics  # noqa: E402
from services.quick_answers import quick_answer  # noqa: E402
from services.senegal_knowledge import format_senegal_knowledge  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = (ROOT / "static" / "home.js").read_text(encoding="utf-8")


def _payload(body):
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


# --- Serveur --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("extra", [{}, {"audience": "inconnu"}, {"audience": "general"}])
def test_sans_profil_choisi_teranga_repond_pour_tout_le_senegal(extra):
    payload = _payload({"message": "Comment refaire ma carte d'identité ?", "language": "fr", **extra})
    assert payload["audience"] == "general"
    assert "Profil actif : tout le Sénégal" in payload["instructions"]
    assert "Profil actif : touriste" not in payload["instructions"]


def test_les_quatre_profils_restent_au_choix():
    for audience in ("tourist", "resident", "diaspora", "merchant"):
        assert _payload({"message": "Bonjour Dakar", "language": "fr", "audience": audience})["audience"] == audience


def test_la_consigne_generale_existe_dans_chaque_langue_et_ne_privilegie_aucun_public():
    for language in ("fr", "en", "wo", "ff"):
        consigne = _AUDIENCE_INSTRUCTIONS["general"][language]
        assert consigne
    fr = _AUDIENCE_INSTRUCTIONS["general"]["fr"]
    for sujet in ("vie quotidienne", "démarches", "santé", "travail", "études", "culture", "voyage"):
        assert sujet in fr
    assert "prioritairement" not in fr


def test_le_planificateur_et_la_voix_acceptent_le_profil_general():
    planner = (ROOT / "services" / "trip_planner.py").read_text(encoding="utf-8")
    realtime = (ROOT / "routes" / "realtime.py").read_text(encoding="utf-8")
    planner_js = (ROOT / "static" / "trip-planner.js").read_text(encoding="utf-8")
    assert '"general"' in planner and '"general"' in realtime
    # Sans « general » ici, ouvrir le planificateur réécrivait le profil mémorisé en « tourist ».
    assert re.search(r'AUDIENCE_VALUES=\[[^\]]*"general"', planner_js)


# --- Accueil --------------------------------------------------------------------------------------------------------

def test_le_bouton_tout_le_senegal_est_le_premier_et_choisi_par_defaut():
    html = app_module.app.test_client().get("/", base_url="https://teranga-ai.fr").get_data(as_text=True)
    boutons = re.findall(r'<button type="button" class="audience-btn( on)?" data-audience="(\w+)" aria-pressed="(\w+)"', html)
    assert [b[1] for b in boutons] == ["general", "tourist", "resident", "diaspora", "merchant"]
    assert boutons[0] == (" on", "general", "true")
    assert all(on == "" and pressed == "false" for on, _, pressed in boutons[1:])
    assert "Tout le Sénégal" in html


def test_le_script_de_l_accueil_part_du_profil_general():
    assert "storageGet('teranga-audience','general')" in HOME_JS
    assert "['general','tourist','resident','diaspora','merchant']" in HOME_JS


def _suggestions_fr():
    bloc = re.search(r"\nfr:\{\n general:\[(.*?)\],\n tourist:", HOME_JS, re.S)
    assert bloc, "suggestions « general » en français introuvables"
    return re.findall(r"\['([^']+)',\"([^\"]+)\"\]", bloc.group(1))


def test_les_suggestions_couvrent_la_vie_de_tous_les_jours_et_pas_seulement_le_voyage():
    suggestions = _suggestions_fr()
    assert len(suggestions) >= 8
    libelles = " ".join(label for label, _ in suggestions)
    for sujet in ("Papiers", "Santé", "Argent", "Études", "Voyage"):
        assert sujet in libelles


@pytest.mark.parametrize("label,question", _suggestions_fr() if re.search(r"\nfr:\{\n general:", HOME_JS) else [("?", "?")])
def test_chaque_suggestion_a_un_appui_verifie(label, question):
    """Une suggestion de l'accueil ne laisse jamais l'IA sans appui : réponse prête, repère vérifié ou fiche de la base."""
    pret = quick_answer({"message": question, "language": "fr"}, {})
    reperes = matching_topics(question)
    base = format_senegal_knowledge(app_module.SENEGAL_KNOWLEDGE, query=question, people=app_module.SENEGAL_PEOPLE)
    fiches = any(titre in base for titre in ("LIEUX PERTINENTS", "PLATS ET BOISSONS", "PANORAMA DU SÉNÉGAL",
                                             "PHRASES WOLOF", "DOSSIER HISTORIQUE"))
    assert pret or reperes or fiches, f"« {question} » ({label}) n'a aucun appui vérifié"
