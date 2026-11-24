"""Teranga répond seul à l'heure de Dakar, au décalage avec Paris et à l'indicatif du Sénégal, sans appeler le modèle.

Faits déjà vérifiés (services/practical_facts.py, sujets « heure » et « sim ») : le Sénégal est à UTC+0 toute l'année,
sans changement d'heure (1 h de moins que Paris en hiver, 2 h en été) ; indicatif +221. L'heure du moment et l'heure
d'été française viennent de la base officielle des fuseaux (zoneinfo, paquet tzdata) : rien n'est inventé.
"""

import datetime as dt
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

import services.quick_answers as qa
from services.quick_answers import quick_answer

ETE = dt.datetime(2026, 7, 15, 12, 0, tzinfo=dt.timezone.utc)
HIVER = dt.datetime(2026, 12, 1, 9, 5, tzinfo=dt.timezone.utc)


def _reponse(message, maintenant=None, monkeypatch=None, language="fr"):
    if maintenant is not None:
        monkeypatch.setattr(qa, "_now_utc", lambda: maintenant)
    answer = quick_answer({"message": message, "language": language}, {})
    return answer["reply"] if answer else None


@pytest.mark.parametrize("message", [
    "Quelle heure est-il à Dakar ?",
    "Il est quelle heure au Sénégal ?",
    "Quel est le décalage horaire entre Paris et Dakar ?",
    "Décalage horaire Sénégal ?",
    "heure à Dakar",
])
def test_l_heure_de_dakar_et_le_decalage_en_hiver(message, monkeypatch):
    reply = _reponse(message, HIVER, monkeypatch)
    assert reply is not None
    assert "À Dakar, il est 9 h 05 (heure du Sénégal, UTC+0)." in reply
    assert "En ce moment, il y a 1 h de moins qu'à Paris (heure d'hiver en France)." in reply
    assert "Le Sénégal ne change jamais d'heure : 1 h de moins que Paris en hiver, 2 h de moins en été." in reply


def test_en_ete_l_ecart_avec_paris_est_de_deux_heures(monkeypatch):
    reply = _reponse("Quelle heure est-il à Dakar ?", ETE, monkeypatch)
    assert "À Dakar, il est 12 h 00 (heure du Sénégal, UTC+0)." in reply
    assert "En ce moment, il y a 2 h de moins qu'à Paris (heure d'été en France)." in reply


def test_le_changement_d_heure_francais_est_suivi_a_la_minute(monkeypatch):
    # Fin de l'heure d'été en France : dimanche 25 octobre 2026 à 01:00 UTC (base officielle des fuseaux).
    avant = _reponse("Décalage horaire Sénégal ?", dt.datetime(2026, 10, 25, 0, 59, tzinfo=dt.timezone.utc), monkeypatch)
    apres = _reponse("Décalage horaire Sénégal ?", dt.datetime(2026, 10, 25, 1, 0, tzinfo=dt.timezone.utc), monkeypatch)
    assert "2 h de moins qu'à Paris" in avant
    assert "1 h de moins qu'à Paris" in apres


@pytest.mark.parametrize("message", [
    "À quelle heure part le ferry pour Gorée ?",
    "Heure de prière à Dakar ?",
    "Combien d'heures de vol entre Paris et Dakar ?",
    "Quelle heure est-il ?",  # sans lieu : l'heure de qui ?
    "Les heures d'ouverture du musée à Dakar",
])
def test_les_autres_questions_sur_les_heures_vont_au_modele(message, monkeypatch):
    reply = _reponse(message, HIVER, monkeypatch)
    assert reply is None or "UTC+0" not in reply


@pytest.mark.parametrize("message", [
    "Indicatif du Sénégal ?",
    "Quel est l'indicatif téléphonique du Sénégal ?",
    "indicatif senegal",
])
def test_l_indicatif_du_senegal(message):
    reply = _reponse(message)
    assert reply is not None
    assert "L'indicatif téléphonique du Sénégal est +221." in reply
    assert "Depuis l'étranger, composez +221 puis le numéro." in reply


@pytest.mark.parametrize("message", [
    "Indicatif de la France ?",
    "Comment avoir une carte SIM avec l'indicatif +221 ?",
])
def test_les_autres_questions_d_indicatif_vont_au_modele(message):
    reply = _reponse(message)
    assert reply is None or "+221 puis le numéro" not in reply


def test_en_anglais_le_modele_repond(monkeypatch):
    assert _reponse("What time is it in Dakar?", HIVER, monkeypatch, language="en") is None
