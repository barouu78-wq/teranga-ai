"""La question en cours n'est comptée qu'une fois dans le contexte de l'IA, et « Préciser ma demande » reste ce bouton.

Bug A : le site envoie la question deux fois, dans `message` et en dernier élément de `history`
(static/home.js, `ask`). `contextual_query` (services/intelligence.py) la reprenait des deux côtés : ses mots
pesaient double dans le choix des lieux (services/senegal_knowledge.py), et « taxi aibd dakar combien »
ramenait 8 lieux au lieu de 2 (Gorée, Saint-Louis, Touba… parce qu'ils citent Dakar une fois).

Bug B : le serveur ajoutait le lieu à « Préciser ma demande » (« Préciser ma demande à dakar ») ; la page,
qui comparait le texte exact, envoyait alors ce libellé comme une question au lieu de remettre le curseur
dans la zone de saisie (test navigateur : tests/e2e/test_boutons_suite.py).
"""

import os
import re
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services.intelligence import build_ux_hints, contextual_query  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def site(message, previous=()):
    """Corps de requête comme static/home.js : la question courante est aussi le dernier élément de history."""
    history = []
    for text in previous:
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": "(réponse)"}]
    history.append({"role": "user", "content": message})
    body = {"message": message, "history": history, "language": "fr", "audience": "tourist"}
    with app.test_request_context("/chat", method="POST", json=body):
        payload, error = parse_chat_payload()
    assert error is None
    return payload


def places(payload):
    """Noms du bloc « LIEUX PERTINENTS » des consignes envoyées au modèle."""
    instructions = payload["instructions"]
    if "LIEUX PERTINENTS :" not in instructions:
        return []
    block = instructions.split("LIEUX PERTINENTS :")[1]
    stop = re.search(r"\n[A-ZÉ][A-ZÉÈ ]{5,}", block)
    return re.findall(r"^- ([^:]+):", block[: stop.start()] if stop else block, re.M)


# Bug A — la question en cours comptée une fois.

def test_la_question_du_site_n_est_comptee_qu_une_fois():
    payload = site("taxi aibd dakar combien")
    assert payload["contextual_query"].count("taxi aibd dakar combien") == 1
    # Mesure sur main : 8 lieux, dont Gorée ; la question seule en ramène 2 (Corniche, Grande Mosquée).
    assert "Île de Gorée" not in places(payload)
    assert len(places(payload)) <= 2


def test_une_vraie_suite_implicite_garde_le_lieu_du_tour_precedent():
    # Garde-fou : retirer la copie de la question ne doit pas retirer le tour d'avant.
    payload = site("Combien de temps faut-il pour la visite ?", previous=("Je veux visiter Gorée",))
    assert "Île de Gorée" in places(payload)


def test_le_dernier_tour_identique_a_la_question_est_ignore_meme_avec_d_autres_espaces():
    history = [
        {"role": "user", "content": "Dakar"},
        {"role": "assistant", "content": "Réponse"},
        {"role": "user", "content": "Et le\nsoir ?"},
    ]
    assert contextual_query(history, "Et le soir ?") == "Dakar | Et le soir ?"


def test_une_question_deja_posee_plus_haut_dans_le_fil_reste_dans_le_contexte():
    # Seul le dernier élément, s'il vient de l'utilisateur, peut être la copie de la question en cours.
    history = [{"role": "user", "content": "Et le soir ?"}, {"role": "assistant", "content": "Réponse"}]
    assert contextual_query(history, "Et le soir ?") == "Et le soir ? | Et le soir ?"


# Bug B — « Préciser ma demande » ne porte jamais de lieu.

def test_preciser_ma_demande_ne_recoit_pas_le_lieu():
    hints = build_ux_hints({"intent": "general_information", "location": "dakar"}, {"place": "dakar"})
    assert hints["followups"][0] == "Préciser ma demande"


def test_preciser_ma_demande_reste_intact_dans_la_reponse_du_site():
    payload = site("Parle-moi de Dakar")
    assert payload["intent_context"]["ux_hints"]["followups"][0] == "Préciser ma demande"


def test_le_service_worker_change_de_version_avec_home_js():
    # v16 : « Préciser ma demande » reconnu même suivi d'un lieu (static/home.js).
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    match = re.search(r"const VERSION = 'teranga-v(\d+)';", sw)
    assert match and int(match.group(1)) >= 16
