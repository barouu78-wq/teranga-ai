"""Une conversation neuve à chaque visite (demande du propriétaire du 5 novembre 2026, vidéo à l'appui).

Avant, la conversation était gardée sans limite dans le téléphone (localStorage) : en revenant des jours plus tard, on
retrouvait encore les questions et les réponses d'avant (une réponse « du lundi 26 octobre » le 5 novembre), et il
fallait faire défiler très loin. Maintenant : pendant une visite (rechargement, aller-retour vers /lieux), la
conversation reste, pour que « et demain ? » marche encore ; après 30 minutes sans activité ou à une nouvelle visite,
le chat repart vide. Rien n'est plus gardé dans localStorage, et une ancienne conversation qui y traînait est effacée.
"""

import datetime
import json
import time


def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def ask(page, text):
    page.fill("#input", text)
    page.click("#send")


ANCIENNE = {"version": 2, "lang": "fr", "history": [
    {"role": "user", "content": "Où trouver une pharmacie de garde ?"},
    {"role": "assistant", "content": "Réponse d'une ancienne visite."},
]}


def _enregistree(page, minutes):
    """Une conversation enregistrée dans l'onglet il y a `minutes` minutes."""
    donnees = dict(ANCIENNE, updatedAt=int(time.time() * 1000) - minutes * 60 * 1000)
    page.evaluate("(d) => sessionStorage.setItem('teranga-history', d)", json.dumps(donnees))


def test_une_conversation_gardee_dans_le_telephone_ne_revient_plus(page, base_url):
    donnees = json.dumps(dict(ANCIENNE, updatedAt=int(time.time() * 1000) - 10 * 24 * 3600 * 1000))
    page.add_init_script(f"localStorage.setItem('teranga-history', {json.dumps(donnees)})")
    page.goto(base_url + "/")
    page.wait_for_timeout(300)
    assert page.locator("#messages .msg").count() == 0
    assert "has-chat" not in (page.get_attribute("body", "class") or "")
    assert page.get_by_text("Réponse d'une ancienne visite.").count() == 0
    assert page.errors == []


def test_la_conversation_n_est_plus_gardee_dans_le_telephone(page, base_url):
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": "Réponse du jour."}),
                                                       content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    page.get_by_text("Réponse du jour.").wait_for(timeout=5000)
    page.wait_for_timeout(400)  # enregistrement différé
    assert page.evaluate("localStorage.getItem('teranga-history')") is None
    assert "Réponse du jour." in page.evaluate("sessionStorage.getItem('teranga-history')")
    assert page.errors == []


def test_un_rechargement_pendant_la_visite_garde_la_conversation(page, base_url):
    page.goto(base_url + "/")
    _enregistree(page, minutes=5)
    page.reload()
    page.get_by_text("Réponse d'une ancienne visite.").wait_for(timeout=5000)
    assert page.errors == []


def test_apres_30_minutes_sans_activite_le_chat_repart_vide(page, base_url):
    page.goto(base_url + "/")
    _enregistree(page, minutes=31)
    page.reload()
    page.wait_for_timeout(300)
    assert page.locator("#messages .msg").count() == 0
    assert page.evaluate("sessionStorage.getItem('teranga-history')") is None
    assert page.errors == []


def test_revenir_sur_l_onglet_apres_30_minutes_vide_le_chat(page, base_url):
    page.clock.install(time=datetime.datetime(2026, 11, 5, 9, 0))
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": "Réponse du matin."}),
                                                       content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    page.get_by_text("Réponse du matin.").wait_for(timeout=5000)
    page.clock.run_for(1000)  # enregistrement différé
    # Onglet laissé ouvert 10 minutes : la conversation reste.
    page.clock.fast_forward("10:00")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    assert page.locator("#messages .msg").count() == 2
    # Puis plus de 30 minutes sans activité : le chat repart vide, sans demander confirmation.
    page.clock.fast_forward("31:00")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(100)
    assert page.locator("#messages .msg").count() == 0
    assert "has-chat" not in (page.get_attribute("body", "class") or "")
    assert page.errors == []
