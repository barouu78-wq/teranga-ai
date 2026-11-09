"""V5, étape 1 (suite) : « Quels sont les jours fériés au Sénégal ? » reçoit tout de suite les prochaines dates du
calendrier vérifié du site (services/events.py), sans appeler le modèle (« Go » du propriétaire, 8 novembre 2026).

Chaque date garde l'étiquette du calendrier (jour férié, fête nationale, fête religieuse) ; une fête lunaire non
confirmée reste « date estimée ». Rien n'est ajouté au calendrier : pas de fête absente du fichier, pas de règle sur ce
qui est férié ou non. Festivals et événements sportifs (jazz, JOJ) ne sont pas des jours fériés : ils ne sont pas
listés. Une date précise (« demain », « le 4 avril »), une année, une question sur une fête ou une suite de
conversation vont au modèle ou à la réponse d'une seule fête.
"""

import datetime as dt
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services import quick_answers
from services.quick_answers import quick_answer

TODAY = dt.date(2026, 11, 8)
LISTE = "\n".join([
    "Prochaines fêtes et jours fériés au Sénégal :",
    "- Noël : 25 décembre 2026 (jour férié)",
    "- Jour de l'an : 1 janvier 2027 (jour férié)",
    "- Korité (Aïd el-Fitr) : 10 mars 2027 (fête religieuse, date estimée)",
    "- Lundi de Pâques : 29 mars 2027 (jour férié)",
    "- Fête de l'Indépendance : 4 avril 2027 (fête nationale)",
    "- Fête du travail : 1 mai 2027 (jour férié)",
    "Les fêtes musulmanes suivent le calendrier lunaire : leur date exacte est fixée quelques jours avant, à "
    "l'observation du croissant de lune.",
    "Toutes les fêtes de l'année : teranga-ai.fr/calendrier-fetes-senegal",
])


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: TODAY)


def _ask(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize("message", [
    "Quels sont les jours fériés au Sénégal ?",
    "Jours fériés au Sénégal",
    "Prochain jour férié ?",
    "Liste des jours fériés",
    "Calendrier des fêtes au Sénégal",
    "Quelles sont les prochaines fêtes au Sénégal ?",
])
def test_la_question_recoit_les_prochaines_dates_du_calendrier(message):
    answer = _ask(message)
    assert answer is not None, message
    assert answer["reply"] == LISTE
    assert answer["theme"] == "fetes"


def test_ni_festival_ni_jeux_dans_la_liste(monkeypatch):
    """Le 8 novembre 2026, les JOJ sont en cours, et le festival de jazz est dans le calendrier : aucun n'est férié."""
    reply = _ask("Quels sont les jours fériés au Sénégal ?")["reply"]
    assert "JOJ" not in reply and "jazz" not in reply


def test_la_liste_part_de_la_date_du_jour(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2026, 10, 19))
    lignes = _ask("Jours fériés au Sénégal")["reply"].split("\n")
    assert lignes[1] == "- Toussaint : 1 novembre 2026 (jour férié)"
    assert len([ligne for ligne in lignes if ligne.startswith("- ")]) == 6


def test_deux_fetes_le_meme_jour_sont_toutes_les_deux_listees(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2027, 8, 10))
    reply = _ask("Jours fériés au Sénégal")["reply"]
    assert "- Assomption : 15 août 2027 (jour férié)" in reply
    assert "- Gamou (Maouloud) : 15 août 2027 (fête religieuse, date estimée)" in reply


def test_la_phrase_sur_la_lune_seulement_si_une_date_est_estimee(monkeypatch):
    noel = {"start": dt.date(2026, 12, 25), "end": None, "name": "Noël", "place": "Tout le pays", "kind": "holiday",
            "confirmed": True, "tips": "", "days_left": 47}
    monkeypatch.setattr(quick_answers, "upcoming_events", lambda today=None, limit=None: [noel])
    reply = _ask("Jours fériés au Sénégal")["reply"]
    assert reply.split("\n")[1] == "- Noël : 25 décembre 2026 (jour férié)"
    assert "croissant de lune" not in reply


def test_apres_la_derniere_date_du_calendrier_le_modele_repond(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2027, 9, 1))
    assert _ask("Quels sont les jours fériés au Sénégal ?") is None


@pytest.mark.parametrize("message", [
    "Est-ce que demain est férié ?",
    "Le 4 avril est-il férié ?",
    "Jours fériés 2025",
    "Quelles fêtes traditionnelles au Sénégal ?",
    "Pourquoi la Toussaint est fériée ?",
    "Les banques sont-elles ouvertes les jours fériés ?",
])
def test_une_date_precise_ou_une_autre_question_va_au_modele(message):
    assert _ask(message) is None, message


def test_une_fete_nommee_garde_sa_propre_reponse():
    assert _ask("C'est quand la Tabaski ?")["reply"].startswith("Tabaski (Aïd el-Kébir) : 17 mai 2027")


def test_une_suite_de_conversation_et_l_anglais_vont_au_modele():
    raw = {"history": [{"role": "user", "content": "Je pars au Sénégal"}, {"role": "assistant", "content": "Super !"},
                       {"role": "user", "content": "Quels sont les jours fériés au Sénégal ?"}]}
    assert _ask("Quels sont les jours fériés au Sénégal ?", raw=raw) is None
    assert _ask("What are the public holidays in Senegal?", language="en") is None
