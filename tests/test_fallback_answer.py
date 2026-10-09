"""Mode autonome : IA en panne, Teranga répond quand même avec sa base vérifiée (aucun appel réseau).

Lieux et plats, repères pratiques (urgences, santé, argent, visa, papiers…), prochaines fêtes, et message
honnête quand rien ne correspond.
"""

import datetime as dt
import inspect
import json
import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services import fallback_answer  # noqa: E402
from services.fallback_answer import MAX_CHARS, MAX_EVENTS, MAX_TOPICS, knowledge_fallback, no_ready_answer  # noqa: E402
from services.practical_facts import TOPICS  # noqa: E402
from services.text import clean_answer  # noqa: E402

B = "https://teranga-ai.fr"
PLACES = app_module.SENEGAL_KNOWLEDGE["places"]
DISHES = app_module.SENEGAL_KNOWLEDGE["dishes"]
# Date fixe : le calendrier des fêtes est écrit en dur et passe avec le temps.
TODAY = dt.date(2026, 10, 8)
FACTS = {name: facts for name, _, facts in TOPICS}
ALL_FACTS = {fact for facts in FACTS.values() for fact in facts}
HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _broken(*_args, **_kwargs):
    raise RuntimeError("Error code: 503 - upstream unavailable")


def _post(monkeypatch, message, json_mode=False, ip=None):
    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", _broken)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", _broken)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    if json_mode:
        headers["X-Teranga-Mode"] = "json"
    # Message unique à chaque appel : jamais servi depuis le cache des réponses.
    extra = {"environ_base": {"REMOTE_ADDR": ip}} if ip else {}
    return client.post("/chat", json={"message": message, "language": "fr"}, headers=headers, base_url=B, **extra)


def test_fallback_uses_the_place_history_and_access():
    places = app_module.SENEGAL_KNOWLEDGE["places"]
    text = knowledge_fallback("Comment visiter Gorée ?", places)
    assert text.startswith("L'assistant IA est momentanément indisponible")
    assert "Île de Gorée (Dakar)" in text and "Comment y aller : Chaloupe" in text
    assert knowledge_fallback("Quel temps fera-t-il demain ?", places) is None


def test_fallback_knows_dishes():
    text = knowledge_fallback("C'est quoi le yassa ?", [], app_module.SENEGAL_KNOWLEDGE["dishes"])
    assert "Yassa" in text


def test_stream_answers_from_the_knowledge_base_when_the_ai_is_down(monkeypatch):
    response = _post(monkeypatch, "Parle-moi de Gorée, panne stream")
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert not any("error" in e for e in events)
    text = "".join(e.get("d", "") for e in events)
    assert "momentanément indisponible" in text and "Gorée" in text
    assert any(e.get("places") for e in events) and events[-1].get("done")


def test_json_mode_answers_from_the_knowledge_base(monkeypatch):
    response = _post(monkeypatch, "Parle-moi de Saint-Louis, panne json", json_mode=True)
    data = response.get_json()
    assert response.status_code == 200 and data["degraded"] is True
    assert "Saint-Louis" in data["reply"]


def test_unknown_topic_still_reports_the_outage(monkeypatch):
    # « Quelle heure est-il à Tokyo ? » déclenche désormais le repère « heure » (mode autonome) : on prend
    # une question que la base ne connaît vraiment pas. Sans `always`, le chat garde son message d'erreur.
    response = _post(monkeypatch, "Qui va gagner le match de ce soir, panne ?", json_mode=True)
    assert response.status_code == 503 and "error" in response.get_json()


def test_stream_never_ends_with_an_empty_bubble(monkeypatch):
    """Flux sans texte puis réponse complète vide : un message s'affiche quand même."""

    class Empty:
        output_text = ""

    def create_response(payload, stream=False):
        return iter([]) if stream else Empty()

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", create_response)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat", json={"message": "Question sans réponse du modèle 42", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": B}, base_url=B,
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    text = "".join(e.get("d", "") for e in events)
    assert "pas réussi à répondre" in text and events[-1].get("done")


# --- Mode autonome : repères pratiques, fêtes, message honnête -------------------------------------------------


def _fallback(question, lang="fr", **kwargs):
    return knowledge_fallback(question, PLACES, DISHES, lang, today=TODAY, **kwargs)


def _blocks(text):
    """Blocs du milieu : entre l'introduction et la phrase finale."""
    return text.split("\n\n")[1:-1]


def _bullets(text):
    return [line[2:] for line in text.splitlines() if line.startswith("• ")]


# (question, sujet, titre attendu) : un cas par grande famille de repères.
FAMILLES = [
    ("Quel est le numéro de la police ?", "urgences", "Urgences et sécurité"),
    ("Y a-t-il du paludisme au Sénégal ?", "sante", "Santé"),
    ("Combien valent 100 euros en FCFA ?", "argent", "Argent et paiements"),
    ("Comment éviter les arnaques ?", "arnaques", "Arnaques à éviter"),
    ("J'ai envoyé de l'argent Wave au mauvais numéro", "mobile_money", "Mobile money"),
    ("Faut-il un visa pour le Sénégal ?", "visa", "Entrée au Sénégal (visa)"),
    ("Comment renouveler ma carte d'identité ?", "papiers", "Papiers et état civil"),
    ("Comment acheter du courant Woyofal ?", "factures", "Électricité prépayée (Woyofal)"),
    ("Comment fonctionne la CMU ?", "protection", "Santé et protection sociale"),
    ("Comment s'inscrire sur Campusen après le bac ?", "etudes", "Études et bourses"),
    ("Comment acheter un terrain au Sénégal ?", "foncier", "Terrain et immobilier"),
]


@pytest.mark.parametrize("question,topic,title", FAMILLES, ids=[q for q, _, _ in FAMILLES])
def test_practical_facts_are_used_as_they_are(question, topic, title):
    text = _fallback(question)
    assert text.startswith("L'assistant IA est momentanément indisponible")
    assert text.endswith("Réessaie dans un moment pour une réponse complète et personnalisée.")
    assert title in text.splitlines()
    # Le premier repère du sujet est repris mot pour mot : ni reformulé, ni complété.
    assert FACTS[topic][0] in text


def test_emergency_numbers_come_from_the_verified_facts():
    text = _fallback("Quel est le numéro de la police ?")
    assert "Police 17, Sapeurs-pompiers 18, SAMU (urgence médicale) 1515" in text
    assert text.count("Urgences et sécurité") == 1 and len(_bullets(text)) == len(FACTS["urgences"])


def test_money_answer_has_the_exact_rate():
    assert "1 € = 655,957 FCFA" in _fallback("Combien valent 100 euros en FCFA ?")


def test_every_bullet_is_a_verified_fact_never_cut():
    for question, _topic, _title in FAMILLES:
        bullets = _bullets(_fallback(question))
        assert bullets and all(bullet in ALL_FACTS for bullet in bullets), question


def test_every_practical_topic_has_a_title():
    assert set(FACTS) <= set(fallback_answer._TITLES)


def test_place_then_practical_facts_when_both_are_asked():
    text = _fallback("Comment aller à Gorée en taxi ?")
    assert "Île de Gorée (Dakar)" in text and "Transports" in text
    assert text.index("Île de Gorée") < text.index("Transports")


# Taille : 3 sujets au plus, un plafond de caractères, jamais un repère coupé.


def test_at_most_three_topics_even_when_the_question_matches_more():
    question = "arnaque mobile money, carte d'identité, visa, prises électriques et taxi"
    text = _fallback(question)
    assert len(_blocks(text)) == MAX_TOPICS == 3
    for block in _blocks(text):
        title, *lines = block.split("\n")
        assert not title.startswith("•") and lines and all(line.startswith("• ") for line in lines)
    # Les trois sujets les plus précis gardent chacun leur premier repère.
    for topic in ("arnaques", "mobile_money", "papiers"):
        assert FACTS[topic][0] in text


def test_long_topic_is_shortened_by_whole_facts():
    text = _fallback("Comment éviter les arnaques ?")
    bullets = _bullets(text)
    assert 0 < len(bullets) < len(FACTS["arnaques"])
    assert sum(len(b) for b in bullets) <= MAX_CHARS
    assert bullets == list(FACTS["arnaques"][: len(bullets)])  # les premiers repères, dans l'ordre
    assert len(text) < 4000


def test_every_family_answer_stays_short():
    for question, _topic, _title in FAMILLES:
        assert len(_fallback(question)) < 4000, question


# Fêtes : calendrier de services/events.py, dates lunaires « estimées ».


def test_named_feast_is_answered_from_the_calendar_with_an_estimated_date():
    text = _fallback("C'est quand la Tabaski ?")
    assert "Prochaines fêtes et événements" in text
    assert "Tabaski (Aïd el-Kébir)" in text and "17 mai 2027 (date estimée, à confirmer)" in text
    assert len(_bullets(text)) == 1  # seule la fête demandée


def test_confirmed_feast_is_marked_confirmed():
    text = _fallback("Quand est Noël au Sénégal ?")
    assert "25 décembre 2026 (date confirmée)" in text


def test_general_holiday_question_lists_the_next_three_feasts_in_order():
    text = _fallback("Quels sont les prochains jours fériés ?")
    lines = _bullets(text)
    assert len(lines) == MAX_EVENTS == 3
    assert [line.split(" — ")[0] for line in lines] == ["Toussaint", "Noël", "Jour de l'an"]


def test_passed_feast_is_not_offered():
    # Après le 17 mai 2027, la Tabaski 2027 est passée : rien ne correspond plus dans le calendrier.
    assert knowledge_fallback("C'est quand la Tabaski ?", PLACES, DISHES, "fr", today=dt.date(2027, 6, 1)) is None


def test_aid_alone_shows_both_aid_feasts():
    text = _fallback("C'est quand l'Aïd ?")
    assert "Korité (Aïd el-Fitr)" in text and "Tabaski (Aïd el-Kébir)" in text


def test_feast_answer_is_not_mixed_with_unrelated_practical_facts():
    assert len(_blocks(_fallback("Quand a lieu le Gamou ?"))) == 1


def test_place_and_its_feast_are_both_answered():
    text = _fallback("Quand a lieu le Grand Magal de Touba ?")
    assert "Touba (Diourbel)" in text and "Grand Magal de Touba — Touba : 23 juillet 2027 (date estimée, à confirmer)" in text


# Rien ne correspond : message honnête, jamais d'invention.

NOTHING = [
    "Quelle est la capitale du Japon ?",
    "Raconte-moi une blague",
    "Qui a gagné la dernière Coupe d'Afrique ?",
    "Écris un poème sur la mer",
    "Qui joue dans le film L'Arnaque avec Paul Newman ?",
    "Je suis volontaire pour une ONG au Sénégal",
    "Quel est le code postal de Dakar ?",
    "Organiser une fête d'anniversaire à Dakar",
    "Where can I get first aid training?",
    "Quand commence le Ramadan ?",
    "Un steak saignant s'il vous plaît",
    "Il fait étouffant à Dakar",
]


@pytest.mark.parametrize("question", NOTHING)
def test_off_topic_question_gets_no_practical_fact_and_no_feast(question):
    assert _fallback(question) is None


@pytest.mark.parametrize("question", NOTHING)
def test_nothing_matches_gives_an_honest_message_with_useful_pages(question):
    text = _fallback(question, always=True)
    assert "momentanément indisponible" in text and "pas de réponse prête" in text and "ne rien inventer" in text
    for path in ("/lieux", "/urgences", "/calendrier-fetes-senegal", "/trip-planner"):
        assert f"teranga-ai.fr{path}" in text
    assert text.endswith("Réessaie dans un moment pour une réponse complète et personnalisée.")
    # Ni numéro d'urgence ni repère : la question ne touche pas à une urgence.
    assert "1515" not in text and "Police 17" not in text
    assert not any(fact in text for fact in ALL_FACTS)


def test_the_suggested_pages_exist_on_the_site():
    client = app_module.app.test_client()
    for path in re.findall(r"teranga-ai\.fr(/\S*)", no_ready_answer("Quelle est la capitale du Japon ?")):
        response = client.get(path, base_url=B, environ_base={"REMOTE_ADDR": "198.51.100.21"})
        assert response.status_code == 200, path


URGENT = [
    "Mon voisin est inconscient",
    "Il y a un incendie dans mon immeuble",
    "Mon fils s'est noyé dans la piscine, au secours",
]


@pytest.mark.parametrize("question", URGENT)
def test_emergency_numbers_only_when_the_question_is_an_emergency(question):
    # Même sans `always` : une urgence ne reçoit jamais une erreur sèche.
    for text in (_fallback(question), _fallback(question, always=True)):
        assert FACTS["urgences"][0] in text
        assert "Police 17" in text and "Sapeurs-pompiers 18" in text and "1515" in text
        assert "pas de réponse prête" in text and "teranga-ai.fr/lieux" in text


def test_english_emergency_without_known_topic_gets_the_numbers():
    text = _fallback("He is drowning!", "en")
    assert "In an emergency" in text and "Police 17" in text and "temporarily unavailable" in text


def test_urgence_words_that_are_not_emergencies_do_not_trigger_the_numbers():
    for question in ("Un steak saignant s'il vous plaît", "Il fait étouffant à Dakar", "What is first aid for burns?"):
        assert "1515" not in _fallback(question, always=True), question


# Anglais : titres et phrases d'accueil traduits, repères repris en français.


def test_english_question_gets_english_frame_and_french_facts():
    text = _fallback("What number do I call for an emergency in Senegal?", "en")
    assert text.startswith("The AI assistant is temporarily unavailable.")
    assert text.endswith("Please try again in a moment for a complete answer.")
    assert "Emergencies and safety" in text and FACTS["urgences"][0] in text
    assert "momentanément" not in text


def test_english_feast_and_no_answer():
    text = _fallback("When is Tabaski?", "en")
    assert "Upcoming holidays and events" in text and "estimated date, to be confirmed" in text
    none = _fallback("What is the capital of Japan?", "en", always=True)
    assert "no ready answer" in none and "make anything up" in none and "teranga-ai.fr/lieux" in none
    assert "Réessaie" not in none and "indisponible" not in none


# Compatibilité des appels existants.


def test_signature_only_gained_optional_keyword_parameters():
    params = inspect.signature(knowledge_fallback).parameters
    assert list(params)[:4] == ["message", "places", "dishes", "lang"]
    assert params["dishes"].default == () and params["lang"].default == "fr"
    for name in list(params)[4:]:
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY and params[name].default is not inspect.Parameter.empty
    # Appel positionnel comme dans routes/chat.py.
    assert knowledge_fallback("Parle-moi de Gorée", PLACES, DISHES, "fr").startswith("L'assistant IA")
    assert knowledge_fallback("Quelle est la capitale du Japon ?", PLACES, DISHES, "fr") is None


# Texte brut : aucune balise, et le nettoyage du chat n'y change rien.


def _texts_to_check():
    questions = [q for q, _, _ in FAMILLES] + NOTHING + URGENT + ["C'est quand la Tabaski ?", "Quels sont les jours fériés ?"]
    for question in questions:
        yield _fallback(question, always=True)
        yield _fallback(question, "en", always=True)
    for place in PLACES:
        yield _fallback(f"Parle-moi de {place['name']}", always=True)
    for dish in DISHES:
        yield _fallback(f"C'est quoi {dish['name']} ?", always=True)


def test_text_has_no_html_tag():
    for text in _texts_to_check():
        assert text and not HTML_TAG.search(text)


def test_text_is_stable_through_the_chat_cleaning():
    for question in [q for q, _, _ in FAMILLES] + NOTHING + URGENT + ["C'est quand la Tabaski ?"]:
        for lang in ("fr", "en"):
            text = _fallback(question, lang, always=True)
            assert clean_answer(text) == text, question


# Branchement réel : le chat répond avec ces repères quand l'IA est en panne.


def test_stream_answers_with_practical_facts_when_the_ai_is_down(monkeypatch):
    response = _post(monkeypatch, "Quel est le numéro de la police ? panne stream", ip="198.51.100.22")
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert not any("error" in e for e in events)
    text = "".join(e.get("d", "") for e in events)
    assert "momentanément indisponible" in text and "Police 17" in text
    assert events[-1].get("degraded") and events[-1].get("done")


def test_json_mode_answers_with_practical_facts_when_the_ai_is_down(monkeypatch):
    response = _post(monkeypatch, "Combien valent 100 euros en FCFA, panne json ?", json_mode=True, ip="198.51.100.23")
    data = response.get_json()
    assert response.status_code == 200 and data["degraded"] is True
    assert "1 € = 655,957 FCFA" in data["reply"]


def test_json_mode_answers_a_feast_question_when_the_ai_is_down(monkeypatch):
    from services import events

    monkeypatch.setattr(fallback_answer, "upcoming_events", lambda today=None, limit=None: events.upcoming_events(TODAY, limit))
    response = _post(monkeypatch, "C'est quand la Tabaski, panne feast ?", json_mode=True, ip="198.51.100.24")
    data = response.get_json()
    assert response.status_code == 200 and data["degraded"] is True
    assert "17 mai 2027 (date estimée, à confirmer)" in data["reply"]


def test_json_mode_gives_the_emergency_numbers_even_for_an_unlisted_emergency(monkeypatch):
    response = _post(monkeypatch, "Il y a un incendie dans mon immeuble, panne json", json_mode=True, ip="198.51.100.25")
    data = response.get_json()
    assert response.status_code == 200 and data["degraded"] is True
    assert "Sapeurs-pompiers 18" in data["reply"] and "pas de réponse prête" in data["reply"]
