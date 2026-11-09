"""V5, étape 1 (suite) : Teranga répond seul à « Faut-il un visa pour le Sénégal ? » et à « Comment envoyer de l'argent
au Sénégal ? », sans appeler le modèle (« Continue » du propriétaire, 7 novembre 2026).

Ces deux questions font partie des questions fréquentes du nouvel accueil (thèmes « Voyage » et « Argent »). La réponse
est le repère vérifié de services/practical_facts.py, tel quel (sujets « visa » et « envoi_argent ») : le même texte
que celui que l'IA reçoit, avec « à vérifier » là où les règles et les frais changent. Seule une question courte qui ne
demande que ça est servie ainsi : une nationalité, un autre pays, une situation (visa à prolonger, argent mal envoyé),
un montant, une suite de conversation ou une autre langue que le français vont au modèle.
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
    ("Faut-il un visa pour le Sénégal ?", "visa", "visa"),
    ("Visa pour le Sénégal ?", "visa", "visa"),
    ("Visa Sénégal", "visa", "visa"),
    ("Ai-je besoin d'un visa pour aller au Sénégal ?", "visa", "visa"),
    ("Faut-il un visa pour visiter le Sénégal ?", "visa", "visa"),
    ("Le visa est-il obligatoire pour le Sénégal ?", "visa", "visa"),
    ("Comment envoyer de l'argent au Sénégal ?", "envoi_argent", "argent"),
    ("Comment comparer deux transferts d'argent ?", "envoi_argent", "argent"),
    ("Transfert d'argent vers le Sénégal", "envoi_argent", "argent"),
    ("Quel service pour envoyer de l'argent au Sénégal ?", "envoi_argent", "argent"),
    ("Comment envoyer de l'argent à ma famille au Sénégal ?", "envoi_argent", "argent"),
    ("Meilleur moyen d'envoyer de l'argent au Sénégal ?", "envoi_argent", "argent"),
])
def test_la_question_recoit_le_repere_verifie(message, sujet, theme):
    answer = _reponse(message)
    assert answer is not None, message
    assert answer["reply"] == "\n".join(_faits(sujet))
    assert answer["theme"] == theme


@pytest.mark.parametrize("message", [
    # Visa : un autre pays, une nationalité, une situation, un autre sens.
    "Comment obtenir un visa pour la France depuis Dakar ?",
    "Visa pour le Canada ?",
    "Faut-il un visa pour un Nigérian ?",
    "Comment prolonger mon visa au Sénégal ?",
    "Faux visa sur internet, est-ce une arnaque ?",
    "Visa étudiant pour le Sénégal ?",
    "Carte Visa acceptée à Dakar ?",
    "Que peux-tu faire pour mon visa ?",
    # Envoi d'argent : une situation, un montant, un autre sens, l'autre sens du transfert.
    "J'ai envoyé de l'argent au mauvais numéro, que faire ?",
    "Mon transfert d'argent n'est pas arrivé",
    "Envoyer de l'argent par Wave, combien de frais ?",
    "Comment envoyer un colis au Sénégal ?",
    "Transfert aéroport Dakar ?",
    "Comment envoyer de l'argent du Sénégal vers la France ?",
    # Relecture Gitar de #584 : le départ du Sénégal est le sens inverse du repère « vers le Sénégal ».
    "Comment envoyer de l'argent du Sénégal ?",
    "Transfert d'argent de Dakar",
    "Envoyer de l'argent depuis le Sénégal",
])
def test_une_situation_ou_un_autre_sujet_va_au_modele(message):
    assert _reponse(message) is None, message


def test_un_montant_garde_le_calcul_du_transfert():
    """« Envoi de 100 euros » : le calcul existant (écart de change), pas le repère général."""
    answer = _reponse("J'ai envoyé 100 euros et ils ont reçu 64 000 FCFA")
    assert answer is None or answer["reply"] != "\n".join(_faits("envoi_argent"))


def test_une_suite_de_conversation_va_au_modele():
    raw = {"history": [{"role": "user", "content": "Je pars au Sénégal"}, {"role": "assistant", "content": "Super !"},
                       {"role": "user", "content": "Faut-il un visa pour le Sénégal ?"}]}
    assert _reponse("Faut-il un visa pour le Sénégal ?", raw=raw) is None


def test_en_anglais_le_modele_repond():
    assert _reponse("Do I need a visa for Senegal?", language="en") is None
    assert _reponse("How do I send money to Senegal?", language="en") is None
