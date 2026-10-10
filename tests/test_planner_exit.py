"""Le mode planification ne reste pas collé : une question autonome en sort, une retouche du plan y reste.

Avant, « Que veut dire teranga ? » posée après une demande de séjour restait en mode planification (consigne
« MODE PLANIFICATION ACTIF », modèle complexe, 1200 jetons) pendant 3 à 4 tours, tant que la demande de séjour
restait dans les derniers messages : `should_use_planner` lisait la durée et le budget du fil entier.

Les corps de requête reproduisent static/home.js : la question courante est déjà le dernier élément de
``history`` au moment de l'envoi. Aucun appel réseau : seul le fournisseur d'IA est simulé.
"""

import json
import os
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

import app as app_module
from services.intelligence import build_intent_context, continues_plan, infer_senegal_context, should_use_planner

B = "https://teranga-ai.fr"
FAST_MODEL = "gpt-5.6-luna"
COMPLEX_MODEL = "gpt-5.6-sol"
ACTIVE = "MODE PLANIFICATION ACTIF"


def turn(role, content):
    return {"role": role, "content": content}


def parse(message, history=()):
    body = {"message": message, "history": [*history, turn("user", message)], "language": "fr", "audience": "tourist"}
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def model_of(payload):
    return app_module._CHAT_SERVICE["model_kwargs"](payload, False)["model"]


PLAN = [
    turn("user", "Planifie un séjour de 5 jours à Saint-Louis avec 300000 FCFA en famille"),
    turn("assistant", "Jour 1 : arrivée à Saint-Louis et visite de l'île. Jour 2 : Langue de Barbarie."),
]

# Questions qui ont leur propre sujet et ne renvoient pas au plan.
AUTONOMES = [
    "Que veut dire teranga ?",
    "Quelle langue parle-t-on au Sénégal ?",
    "C'est quoi le thiéboudienne ?",
    "Comment dit-on merci en wolof ?",
    "Qui était Léopold Sédar Senghor ?",
    "Où se trouve le lac Rose ?",
    "Combien d'habitants a Dakar ?",
    "Quel est le taux de change euro FCFA ?",
    "Comment fonctionne Wave ?",
    "Quel temps fait-il ce matin à Saint-Louis ?",
    "Faut-il un visa pour entrer au Sénégal ?",
    "Peut-on boire l'eau du robinet à Dakar ?",
    "Casamance : quelle est la meilleure saison ?",
    "Quels sont les numéros d'urgence ?",
    "Combien valent 100 euros en FCFA ?",
    "Quel jour est la Tabaski ?",
    "Is tap water safe to drink?",
    "What does teranga mean?",
]

# Retouches et précisions du plan en cours : elles restent en mode planification.
SUIVIS = [
    "Mets plutôt 3 jours",
    "Détaille le deuxième jour",
    "Et pour deux personnes ?",
    "Ajoute une activité le soir du jour 2",
    "Peux-tu réduire le budget ?",
    "Remplace le jour 3 par Lompoul",
    "Et en famille avec 2 enfants ?",
    "Plus économique",
    "Rends-le moins cher",
    "Pour 2 semaines plutôt",
    "Avec un budget de 500000 FCFA",
    "Et si on partait en juillet ?",
    "Ça marche pour des enfants de 5 ans ?",
    "Quel hôtel prendre pour la nuit 2 ?",
    "Supprime la visite de l'île",
    "Je voudrais plutôt une version plus tranquille",
    "Peux-tu ajouter un jour à Lompoul ?",
    "Garde le même budget mais avec une plage",
    "Le deuxième jour est trop chargé",
    "C'est trop cher",
    "Continue",
    "Précise",
    "Make it 3 days instead",
    "And for two people?",
    "Can you shorten the second day?",
]


@pytest.mark.parametrize("question", AUTONOMES)
def test_standalone_question_leaves_the_planning_mode(question):
    payload = parse(question, PLAN)
    assert payload["planner"] is False
    assert ACTIVE not in payload["instructions"] and "Mode planification recommandé : non." in payload["instructions"]
    assert model_of(payload) == FAST_MODEL


@pytest.mark.parametrize("message", SUIVIS)
def test_plan_follow_up_keeps_the_planning_mode(message):
    payload = parse(message, PLAN)
    assert payload["planner"] is True
    assert ACTIVE in payload["instructions"]
    assert model_of(payload) == COMPLEX_MODEL


def test_the_planning_mode_no_longer_sticks_for_four_turns():
    """Le défaut mesuré : la question autonome restait en planification aux tours 1, 2 et 3 après le séjour."""
    history = list(PLAN)
    for tour in range(1, 6):
        payload = parse("Que veut dire teranga ?", history)
        assert payload["planner"] is False, f"tour {tour}"
        history += [turn("user", "Que veut dire teranga ?"), turn("assistant", "Teranga veut dire hospitalité en wolof.")]


def test_a_follow_up_still_continues_the_plan_after_an_unrelated_question():
    history = [*PLAN, turn("user", "Que veut dire teranga ?"), turn("assistant", "L'hospitalité, en wolof.")]
    assert parse("Mets plutôt 3 jours", history)["planner"] is True
    assert parse("Détaille le deuxième jour", history)["planner"] is True


@pytest.mark.parametrize("request_text", [
    "Planifie un séjour de 3 jours à Dakar avec 200000 FCFA",
    "Que faire pendant les vacances à Saly ?",
    "Organise un séjour de 4 jours à Kédougou",
])
def test_a_new_planning_request_is_still_a_plan(request_text):
    """La question a ses propres signaux de planification : elle déclenche le mode, avec ou sans plan avant elle."""
    assert parse(request_text, [])["planner"] is True
    unrelated = [turn("user", "Que veut dire teranga ?"), turn("assistant", "L'hospitalité, en wolof.")]
    assert parse(request_text, unrelated)["planner"] is True


def test_first_turn_is_unchanged():
    assert parse("Que veut dire teranga ?", [])["planner"] is False
    assert parse(PLAN[0]["content"], [])["planner"] is True


def test_context_flags():
    assert infer_senegal_context([], "Que veut dire teranga ?")["standalone_request"] is False  # rien avant
    context = infer_senegal_context(PLAN, "Que veut dire teranga ?")
    assert context["standalone_request"] is True and context["message"] == "Que veut dire teranga ?"
    assert infer_senegal_context(PLAN, "Mets plutôt 3 jours")["standalone_request"] is False
    assert infer_senegal_context(PLAN, "")["standalone_request"] is False


def test_should_use_planner_still_accepts_a_plain_context():
    """Un contexte construit à la main (sans `standalone_request`) garde l'ancien comportement."""
    assert should_use_planner({"query": "planifie un sejour de 4 jours", "intents": ["travel"], "duration": "4 jours"}) is True
    assert should_use_planner({"query": "que veut dire teranga", "intents": ["culture"]}) is False


def test_the_standalone_check_uses_only_the_current_request():
    context = infer_senegal_context(PLAN, "Que veut dire teranga ?")
    assert context["duration"] == "5 jours" and context["budget"]  # le fil porte bien un séjour chiffré
    assert should_use_planner(context) is False
    assert should_use_planner({**context, "standalone_request": False}) is True  # sans la règle : l'ancien défaut


@pytest.mark.parametrize("message,expected", [
    ("Pourquoi ?", True), ("Et demain ?", True), ("Plus court", True), ("Précise", True),
    ("Détaille le deuxième jour", True), ("Ajoute une activité le soir du jour 2", True), ("Et pour deux personnes ?", True),
    ("Cap Skirring, c'est loin de Ziguinchor ?", False),  # « ca… » n'est pas « ça »
    ("Casamance : quelle est la meilleure saison ?", False),
    ("Quelle est la capitale du Sénégal ?", False),
    ("Change de la monnaie à Dakar, où aller ?", True),  # début en « change » : prudence, on garde l'ancien comportement
    ("Is it safe to swim at Ngor beach in the evening?", False),  # phrase longue qui a son propre sujet
])
def test_continues_plan_edge_cases(message, expected):
    assert continues_plan(message) is expected


@pytest.mark.parametrize("question", [
    "Capitale du Sénégal ?",
    "Casamance : quelle est la meilleure saison ?",
    "Cadeaux typiques à rapporter ?",
])
def test_a_question_starting_with_ca_is_not_a_follow_up(question):
    """« ça » normalisé donne « ca » : toute question commençant par « Ca… » était prise pour une relance, donc
    héritait l'intention du fil (météo, séjour) et, après un plan, le modèle complexe."""
    weather = [turn("user", "Quelle météo à Dakar aujourd'hui ?"), turn("assistant", "Ciel dégagé, environ 31 degrés.")]
    intent = build_intent_context(question, [*weather, turn("user", question)])
    assert intent["intent"] == "general_information" and intent["domain"] != "weather"
    payload = parse(question, PLAN)
    assert payload["intent_context"]["intent"] != "trip_planning" and payload["planner"] is False
    assert payload["deep_reasoning"] is False and model_of(payload) == FAST_MODEL


@pytest.mark.parametrize("follow_up", ["Ça coûte combien ?", "ça marche pour les enfants ?", "Cela change quoi ?", "Et demain ?"])
def test_real_short_follow_ups_still_inherit_the_intent(follow_up):
    weather = [turn("user", "Quelle météo à Dakar aujourd'hui ?"), turn("assistant", "Ciel dégagé, environ 31 degrés.")]
    assert build_intent_context(follow_up, [*weather, turn("user", follow_up)])["intent"] == "weather"


def test_end_to_end_the_provider_receives_the_fast_model_instructions(monkeypatch):
    """Requête complète avec faux fournisseur : la consigne de planification n'est pas envoyée à une question autonome."""
    seen = {}

    def fake_create_response(payload, stream=False):
        seen["payload"] = payload
        seen["kwargs"] = app_module._CHAT_SERVICE["model_kwargs"](payload, stream)
        yield SimpleNamespace(type="response.output_text.delta", delta="Teranga veut dire hospitalité.")
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text="Teranga veut dire hospitalité.", status="completed"))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_create_response)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    message = "Que veut dire teranga ?"
    body = {"message": message, "history": [*PLAN, turn("user", message)], "language": "fr", "audience": "tourist"}
    response = client.post("/chat", json=body, headers={"X-CSRF-Token": token, "Origin": B}, base_url=B,
                           environ_base={"REMOTE_ADDR": "198.51.100.61"})
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert "".join(e.get("d", "") for e in events).startswith("Teranga veut dire")
    assert seen["payload"]["planner"] is False and ACTIVE not in seen["payload"]["instructions"]
    assert seen["kwargs"]["model"] == FAST_MODEL and seen["kwargs"]["max_output_tokens"] == 800
