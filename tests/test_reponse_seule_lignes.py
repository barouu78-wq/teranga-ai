"""V5, étape 1 (suite) : Teranga répond seul avec la ligne précise d'un repère vérifié (« Go » du propriétaire,
7 novembre 2026).

Pour une question courte qui ne demande qu'une chose (« Où trouver une pharmacie de garde ? »), la réponse est la ligne
correspondante de services/practical_facts.py, telle quelle : le texte que l'IA reçoit aussi, avec ses sources dans ce
fichier et « à vérifier » là où les règles changent. Pas le repère entier (la pharmacie n'a rien à faire du vaccin
contre la fièvre jaune). Une situation (« j'ai le palu », « carte perdue », « code oublié »), un détail, une suite de
conversation ou une autre langue que le français vont au modèle.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services import practical_facts
from services.quick_answers import _LINE_ASKS, quick_answer


def _lignes(sujet, *debuts):
    faits = next(facts for name, _, facts in practical_facts.TOPICS if name == sujet)
    return "\n".join(next(f for f in faits if f.startswith(debut)) for debut in debuts)


def _reponse(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize(("message", "sujet", "debuts", "theme"), [
    # Santé
    ("Où trouver une pharmacie de garde ?", "sante", ("Pharmacie de garde",), "sante"),
    ("Pharmacie de garde à Dakar", "sante", ("Pharmacie de garde",), "sante"),
    ("Pharmacie ouverte la nuit à Dakar ?", "sante", ("Pharmacie de garde",), "sante"),
    ("Comment se protéger du paludisme ?", "sante", ("Paludisme",), "sante"),
    ("Y a-t-il le paludisme au Sénégal ?", "sante", ("Paludisme",), "sante"),
    ("Peut-on boire l'eau du robinet à Dakar ?", "sante", ("Eau",), "sante"),
    ("L'eau du robinet est-elle potable au Sénégal ?", "sante", ("Eau",), "sante"),
    ("Faut-il le vaccin contre la fièvre jaune ?", "sante", ("Fièvre jaune",), "sante"),
    # Papiers
    ("Comment refaire ma carte d'identité ?", "papiers", ("Carte d'identité",), "papiers"),
    ("Que faut-il pour une carte d'identité ?", "papiers", ("Carte d'identité",), "papiers"),
    ("Renouveler ma carte d'identité", "papiers", ("Carte d'identité",), "papiers"),
    ("Comment faire un passeport ?", "papiers", ("Passeport",), "papiers"),
    ("Renouveler mon passeport sénégalais", "papiers", ("Passeport",), "papiers"),
    ("Comment obtenir un acte de naissance ?", "papiers", ("État civil", "En ligne"), "papiers"),
    ("Comment obtenir un acte de naissance depuis l'étranger ?", "papiers", ("État civil", "En ligne"), "papiers"),
    ("Extrait de naissance", "papiers", ("État civil", "En ligne"), "papiers"),
    ("Comment demander un casier judiciaire ?", "papiers", ("Casier judiciaire", "En ligne"), "papiers"),
    ("Casier judiciaire Sénégal", "papiers", ("Casier judiciaire", "En ligne"), "papiers"),
    # Mobile money
    ("Comment protéger mon code secret Wave ou Orange Money ?", "mobile_money", ("Code secret",), "argent"),
    ("Faut-il donner mon code secret Wave ?", "mobile_money", ("Code secret",), "argent"),
    ("J'ai reçu de l'argent par erreur, que faire ?", "mobile_money", ("Envoi par erreur",), "argent"),
    ("J'ai envoyé de l'argent par erreur sur Wave", "mobile_money", ("Envoi par erreur",), "argent"),
    # Arnaques
    ("« Voici mon nouveau numéro » : est-ce une arnaque ?", "arnaques", ("Faux proche",), "urgences"),
    ("Arnaque au nouveau numéro", "arnaques", ("Faux proche",), "urgences"),
    ("Un SMS d'amende, c'est vrai ?", "arnaques", ("Faux SMS",), "urgences"),
    ("J'ai reçu un SMS d'amende avec un lien, arnaque ?", "arnaques", ("Faux SMS",), "urgences"),
    ("On m'a arnaqué sur Wave, que faire ?", "arnaques", ("Si l'on est victime",), "urgences"),
    ("Je suis victime d'une arnaque, que faire ?", "arnaques", ("Si l'on est victime",), "urgences"),
])
def test_la_question_recoit_la_ligne_verifiee(message, sujet, debuts, theme):
    answer = _reponse(message)
    assert answer is not None, message
    assert answer["reply"] == _lignes(sujet, *debuts), message
    assert answer["theme"] == theme


@pytest.mark.parametrize("message", [
    # Une situation ou un détail : le modèle répond (avec le repère entier dans son contexte).
    "J'ai le palu, que faire ?",
    "Paludisme symptômes chez un enfant",
    "Coupure d'eau à Dakar aujourd'hui",
    "Pharmacie à Saint-Louis ?",
    "Faut-il un vaccin pour le Sénégal ?",
    "Carte d'identité perdue, que faire ?",
    "Faut-il une carte d'identité pour ouvrir un compte ?",
    "Faut-il un passeport pour le Sénégal ?",
    "Passeport perdu à Paris",
    "Comment déclarer la naissance de mon fils ?",
    "J'ai oublié mon code secret Wave",
    "Comment changer mon code secret Orange Money ?",
    "Code secret Woyofal",
    "J'ai envoyé de l'argent au mauvais numéro, que faire ?",
    "Comment avoir un nouveau numéro Orange ?",
    "Nouveau numéro de téléphone",
    "J'ai été arnaqué par un faux policier, que faire ?",
    "Comment éviter les arnaques au Sénégal ?",
])
def test_une_situation_ou_un_detail_va_au_modele(message):
    assert _reponse(message) is None, message


def test_chaque_debut_de_ligne_designe_une_seule_ligne_du_repere():
    """Si une ligne de practical_facts change de début, la réponse prête ne doit pas disparaître en silence."""
    for sujet, debuts, _, _ in _LINE_ASKS:
        faits = next(facts for name, _, facts in practical_facts.TOPICS if name == sujet)
        for debut in debuts:
            assert sum(f.startswith(debut) for f in faits) == 1, (sujet, debut)


def test_une_suite_de_conversation_va_au_modele():
    raw = {"history": [{"role": "user", "content": "Je suis à Dakar"}, {"role": "assistant", "content": "Super !"},
                       {"role": "user", "content": "Où trouver une pharmacie de garde ?"}]}
    assert _reponse("Où trouver une pharmacie de garde ?", raw=raw) is None


def test_en_anglais_le_modele_repond():
    assert _reponse("Where can I find an on-duty pharmacy?", language="en") is None
    assert _reponse("Pharmacie de garde", language="wo") is None
