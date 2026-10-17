"""Recherche web ciblée : quand chercher, où chercher, et avec quelle requête.

Le corps de requête reproduit celui du site : la question courante est le dernier élément de
`history` (static/home.js). Aucun appel réseau : les fournisseurs sont simulés.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import json  # noqa: E402

import pytest  # noqa: E402

from app import app, parse_chat_payload  # noqa: E402
from services import external_research as research  # noqa: E402
from services.model_params import build_model_kwargs, openai_model  # noqa: E402
from services.orchestrator import build_agent_plan  # noqa: E402
from services import web_policy  # noqa: E402
from services.senegal_knowledge import classify_domain  # noqa: E402
from services.web_policy import SOURCE_FILTERS, preferred_domains, reasoning_effort, search_context_size  # noqa: E402


def research_query(payload):
    return web_policy.research_query(payload)


def site(message, previous=(), language="fr", audience="tourist"):
    history = []
    for text in previous:
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": "(réponse)"}]
    history.append({"role": "user", "content": message})
    body = {"message": message, "history": history, "language": language, "audience": audience}
    with app.test_request_context("/chat", method="POST", json=body):
        payload, error = parse_chat_payload()
    assert error is None
    return payload


def allowed_domains(payload):
    plan = build_agent_plan(payload, model=openai_model())
    kwargs = build_model_kwargs(payload, model=plan.model, reasoning_effort=reasoning_effort,
                                search_context_size=search_context_size, preferred_domains=preferred_domains, stream=True)
    return (kwargs["tools"][0].get("filters") or {}).get("allowed_domains", [])


# --- Où chercher : filtres de domaines ---------------------------------------------------------------------------


def test_ferry_price_web_search_is_not_restricted_to_statistics_sites():
    payload = site("prix du ferry pour ziguinchor")
    assert payload["use_web"] is True
    assert "worldbank.org" not in allowed_domains(payload)


@pytest.mark.parametrize("message", ["prix du ferry pour ziguinchor", "horaires chaloupe goree",
                                     "how much is the ferry dakar ziguinchor", "les ferries pour la casamance"])
def test_ferry_and_chaloupe_are_transport(message):
    assert classify_domain(message) == "transport"


@pytest.mark.parametrize("message,domain", [
    ("prix du sac de ciment a dakar", "economy"),
    ("Histoire du royaume du Cayor", "culture"),
    ("Prix d'un taxi de Dakar à l'aéroport AIBD", "transport"),
    ("C'est quoi le Lac Rose ?", "general"),
    ("meteo a dakar demain", "weather"),
])
def test_neighbour_domains_do_not_move(message, domain):
    assert classify_domain(message) == domain


def test_filters_name_the_real_senegalese_government_domain():
    """Les sites officiels sénégalais sont en « .gouv.sn » (servicepublic.gouv.sn, sante.gouv.sn…), pas « .gov.sn »."""
    for domain, domains in SOURCE_FILTERS.items():
        assert "gov.sn" not in domains, domain
    for domain in ("administration", "weather", "society"):
        assert "gouv.sn" in preferred_domains(domain), domain


@pytest.mark.parametrize("domain", ["transport", "travel", "food", "economy", "culture", "environment"])
def test_topics_answered_by_operators_have_no_hard_domain_filter(domain):
    """Ferry, hôtel, restaurant, prix, concert : la réponse est chez l'opérateur, pas au ministère ni à l'ANSD."""
    assert preferred_domains(domain) == ()


@pytest.mark.parametrize("message,previous,expected_first", [
    ("Faut-il un visa pour le Sénégal ?", (), "diplomatie.gouv.sn"),
    ("et demain ?", ("meteo a dakar",), "anacim.sn"),
])
def test_official_topics_keep_their_official_filter(monkeypatch, message, previous, expected_first):
    from services import weather

    def unavailable(*args, **kwargs):
        raise OSError("prévisions indisponibles")

    monkeypatch.setattr(weather, "fetch_forecast", unavailable)  # sans prévision injectée, la recherche web répond
    payload = site(message, previous=previous)
    assert payload["use_web"] is True
    assert allowed_domains(payload)[:1] == [expected_first]
    assert "gouv.sn" in allowed_domains(payload)


@pytest.mark.parametrize("message", ["Où manger du thiéboudienne à Dakar ?", "Meilleurs hôtels à Cap Skirring",
                                     "prix du ferry pour ziguinchor", "Comment créer une entreprise au Sénégal ?"])
def test_operator_questions_search_the_open_web(message):
    payload = site(message)
    assert payload["use_web"] is True
    assert allowed_domains(payload) == []


# --- Quand chercher : faux déclenchements et voisins qui doivent toujours chercher -------------------------------

NO_WEB = [
    ("tourist", "fr", "c est quoi exactement le thieboudienne"),
    ("tourist", "en", "ok now tell me about the pink lake"),
    ("tourist", "en", "what to eat in senegal"),
    ("tourist", "fr", "C'est quoi le Grand Magal ?"),
    ("tourist", "fr", "Que manger au Fouta ?"),
    ("tourist", "fr", "Est-ce dangereux de manger dans la rue ?"),
    ("tourist", "fr", "Quel est le décalage horaire avec Paris ?"),
    ("resident", "fr", "je suis nouveau a dakar, des conseils pour m integrer ?"),
    ("resident", "fr", "hier j ai goute le thiakry, c est fait avec quoi"),
    ("resident", "fr", "qu est ce qui change entre le wolof de dakar et celui de saint louis"),
    ("resident", "fr", "ma tata habite a rufisque, c est quoi l histoire de la ville"),
    ("diaspora", "fr", "c est quoi la teranga exactement"),
    ("diaspora", "fr", "verifie mon message en wolof pour ma maman : jamm nga fanane"),
    ("merchant", "fr", "comment faire la promotion de ma boutique sur whatsapp"),
    ("merchant", "fr", "je viens d ouvrir une nouvelle boutique de tissus, comment attirer des clients"),
    ("merchant", "fr", "ecris une offre pour mes clients fideles"),
    ("merchant", "fr", "comment lancer une ferme avicole a thies"),
    ("merchant", "fr", "verifie l orthographe de mon annonce"),
    ("merchant", "fr", "comment attirer des clientes dans mon salon de coiffure"),
    ("merchant", "fr", "comment ecrire une politique de retour pour ma boutique"),
]

WEB = [
    ("tourist", "fr", "prix du ferry pour ziguinchor"),
    ("tourist", "fr", "horaires chaloupe goree"),
    ("tourist", "en", "is the goree ferry running right now"),
    ("tourist", "en", "where to eat in dakar"),
    ("tourist", "fr", "ou manger un bon thieb a dakar"),
    ("tourist", "fr", "c est quand le magal cette annee"),
    ("tourist", "fr", "Date de la Korité 2027"),
    ("tourist", "fr", "C'est quand la fin du ramadan ?"),
    ("tourist", "en", "When is Tabaski this year?"),
    ("tourist", "fr", "horaires du ter dakar"),
    ("resident", "fr", "quoi de nouveau a dakar ?"),
    ("resident", "fr", "qu est ce qui s est passe hier a dakar"),
    ("resident", "fr", "ou faire le change a dakar"),
    ("resident", "fr", "bureau de change a l aibd"),
    ("resident", "fr", "prendre un tata pour aller a pikine"),
    ("resident", "fr", "le musee est ferme le lundi ?"),
    ("diaspora", "fr", "verifie mon vol paris dakar de demain"),
    ("diaspora", "fr", "taux de change euro fcfa"),
    ("merchant", "fr", "offre d emploi a dakar"),
    ("merchant", "fr", "salon international de l agriculture c est quand"),
    ("merchant", "fr", "actualite politique au senegal"),
    ("merchant", "fr", "nouvelle loi sur le foncier"),
]


@pytest.mark.parametrize("audience,language,message", NO_WEB, ids=[m for _, _, m in NO_WEB])
def test_stable_questions_do_not_search_the_web(audience, language, message):
    assert site(message, language=language, audience=audience)["use_web"] is False


@pytest.mark.parametrize("audience,language,message", WEB, ids=[m for _, _, m in WEB])
def test_neighbour_live_questions_still_search_the_web(audience, language, message):
    assert site(message, language=language, audience=audience)["use_web"] is True


def test_price_follow_up_without_accent_searches_the_web():
    assert site("combien ca coute ?", previous=("je veux aller a goree",))["use_web"] is True


def test_stable_question_after_a_price_question_does_not_inherit_the_web():
    assert site("comment on dit merci en wolof", previous=("prix du taxi aibd dakar",))["use_web"] is False


def test_balanced_battery():
    assert len(NO_WEB) >= 20 and len(WEB) >= 20


# --- Avec quelle requête : la recherche externe ne part plus avec le message brut ---------------------------------


def test_follow_up_query_carries_the_subject_of_the_thread():
    query = research_query(site("et en bus ?", previous=("prix du taxi aibd dakar",)))
    assert "aibd" in query.casefold() and "bus" in query.casefold()


def test_thread_driven_follow_up_query_carries_the_subject():
    query = research_query(site("Et pour les enfants ?", previous=("Quel est le prix du ferry pour Gorée ?",)))
    assert "ferry" in query.casefold() and "enfants" in query.casefold()


def test_standalone_question_query_does_not_drag_the_previous_turn():
    query = research_query(site("taux euro cfa aujourd hui", previous=("comment dire merci en wolof",)))
    assert "merci" not in query.casefold() and "taux euro cfa" in query.casefold()


def test_query_names_the_place_chosen_in_the_interface():
    body = {"message": "c est ouvert ?", "history": [{"role": "user", "content": "c est ouvert ?"}],
            "language": "fr", "audience": "tourist", "context_place": "Gorée"}
    with app.test_request_context("/chat", method="POST", json=body):
        payload, error = parse_chat_payload()
    assert error is None and payload["use_web"] is True
    assert research_query(payload) == "Gorée c est ouvert ?"


def test_query_is_anchored_to_senegal_only_when_needed():
    assert research_query(site("taux euro cfa aujourd hui")).endswith("Sénégal")
    assert research_query(site("prix du ferry pour ziguinchor")) == "prix du ferry pour ziguinchor"
    assert research_query(site("What is the current exchange rate for CFA?", language="en")).endswith("Senegal")


def test_query_drops_email_addresses_and_phone_numbers_but_keeps_amounts():
    query = research_query(site("arnaque ? un certain jean.dupont@example.com m appelle du +221 77 123 45 67 "
                                "et du 06 12 34 56 78 pour un terrain a 300 000 000 fcfa"))
    assert "@" not in query and "example.com" not in query
    assert "77 123 45 67" not in query and "06 12 34 56 78" not in query
    assert "300 000 000 fcfa" in query and "terrain" in query


def test_query_is_bounded_and_keeps_an_explicit_url():
    url = "https://teranga-ai.fr/lieux/ile-de-goree"
    long_message = "prix actuel de la chaloupe " + url + " " + "vraiment " * 200
    assert len(long_message) < 2000  # sous la limite du message : rien n'est coupé avant la requête
    query = research_query(site(long_message))
    assert url in query and query.startswith("prix actuel de la chaloupe")
    assert len(query.replace(url, "")) <= 320


def test_chat_route_sends_the_cleaned_query_to_the_search_provider(monkeypatch):
    import app as app_module

    sent = []

    def fake_tavily(query, max_results=5):
        sent.append(query)
        return {"results": [{"title": "Page", "url": "https://exemple.sn/bus", "content": "Bus AIBD : voir le site."}]}

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr(research, "search_tavily", fake_tavily)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", lambda payload: ("Réponse.", [], None, None))

    client = app_module.app.test_client()
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    history = [{"role": "user", "content": "prix du taxi aibd dakar"}, {"role": "assistant", "content": "(réponse)"},
               {"role": "user", "content": "et en bus ?"}]
    response = client.post(
        "/chat",
        json={"message": "et en bus ?", "history": history, "language": "fr", "audience": "tourist"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr", "X-Teranga-Mode": "json"},
        base_url="https://teranga-ai.fr",
        environ_base={"REMOTE_ADDR": "203.0.113.181"},
    )
    assert response.status_code == 200, json.dumps(response.get_json())
    assert len(sent) == 1
    assert sent[0] != "et en bus ?"
    assert "aibd" in sent[0].casefold() and "bus" in sent[0].casefold()
