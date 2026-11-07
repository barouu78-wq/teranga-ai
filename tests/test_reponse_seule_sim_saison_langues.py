"""V5, étape 1 (suite) : Teranga répond seul aux questions fréquentes sur la carte SIM et les opérateurs, la meilleure
saison pour venir et les langues parlées, sans appeler le modèle (Go V5 du propriétaire, 6 et 7 novembre 2026).

La réponse est le repère vérifié de services/practical_facts.py, tel quel (sujets « sim », « saison » et « langue ») :
le même texte que celui que l'IA reçoit. Seule une question courte qui ne demande que ça est servie ainsi : une
situation, un lieu précis, une date, une suite de conversation ou une autre langue que le français vont au modèle.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services import practical_facts
from services.quick_answers import quick_answer


def _faits(nom):
    return next(facts for name, _, facts in practical_facts.TOPICS if name == nom)


def _reponse(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize(("message", "sujet", "theme"), [
    ("Quel opérateur au Sénégal ?", "sim", "internet"),
    ("Où acheter une carte SIM à Dakar ?", "sim", "internet"),
    ("Comment avoir une puce au Sénégal ?", "sim", "internet"),
    ("Carte SIM Sénégal", "sim", "internet"),
    ("Quelle est la meilleure saison pour visiter le Sénégal ?", "saison", "meteo"),
    ("Quand partir au Sénégal ?", "saison", "meteo"),
    ("Meilleure période pour aller au Sénégal ?", "saison", "meteo"),
    ("C'est quand la saison des pluies ?", "saison", "meteo"),
    ("Climat du Sénégal ?", "saison", "meteo"),
    ("Quelle langue parle-t-on au Sénégal ?", "langue", "langue"),
    ("Langue officielle du Sénégal ?", "langue", "langue"),
    ("Quelles langues sont parlées au Sénégal ?", "langue", "langue"),
])
def test_la_question_recoit_le_repere_verifie(message, sujet, theme):
    answer = _reponse(message)
    assert answer is not None, message
    assert answer["reply"] == "\n".join(_faits(sujet))
    assert answer["theme"] == theme


@pytest.mark.parametrize("message", [
    "Ma carte SIM Orange ne marche plus, que faire ?",
    "Combien coûte un forfait internet Orange ?",
    "Quel opérateur a le meilleur réseau à Kédougou ?",
    "Quand partir de Dakar pour Saint-Louis ?",
    "Saison de la mangue au Sénégal ?",
    "Il pleut demain à Dakar ?",
    "Apprends-moi la langue wolof",
    "Comment dire merci en wolof ?",
    "Langue de bœuf au restaurant ?",
])
def test_une_situation_ou_un_autre_sujet_va_au_modele(message):
    assert _reponse(message) is None, message


def test_une_suite_de_conversation_va_au_modele():
    raw = {"history": [{"role": "user", "content": "Je pars au Sénégal"}, {"role": "assistant", "content": "Super !"},
                       {"role": "user", "content": "Quand partir au Sénégal ?"}]}
    assert _reponse("Quand partir au Sénégal ?", raw=raw) is None


def test_en_anglais_le_modele_repond():
    assert _reponse("When is the best time to visit Senegal?", language="en") is None
