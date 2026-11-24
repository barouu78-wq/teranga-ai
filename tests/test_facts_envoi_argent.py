"""Sujet « envoi_argent » (services/facts/envoi_argent.py) : envoyer de l'argent vers le Sénégal et comparer.

Plan du 19 octobre 2026 (docs/PLAN-DIASPORA.md) : « Comment envoyer de l'argent au Sénégal ? » est une des questions
principales de la diaspora. Le repère dit comment comparer, sans fait nouveau (parité fixe déjà vérifiée).
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import matching_topics, practical_context  # noqa: E402


@pytest.mark.parametrize(
    ("question", "phrase"),
    [
        ("Comment envoyer de l'argent au Sénégal ?", "Envoyer de l'argent vers le Sénégal"),
        ("Quel est le moins cher pour envoyer 200 euros au Sénégal ?", "montant reçu en FCFA"),
        ("Comment envoyer 500 € au Sénégal ?", "montant reçu en FCFA"),
        ("Comment transférer de l'argent à ma mère à Dakar ?", "montant reçu en FCFA"),
        ("Quel est le meilleur moyen d'envoi d'argent vers le Sénégal ?", "montant reçu en FCFA"),
        ("Quel est le moins cher : Wise ou Western Union ?", "montant reçu en FCFA"),
        ("Western Union me donne 640 FCFA pour 1 euro, c'est normal ?", "en dessous de 655,957 FCFA pour 1 €"),
        ("Comment faire un virement vers le Sénégal ?", "montant reçu en FCFA"),
        ("Sending money to Senegal from France, what is cheapest?", "montant reçu en FCFA"),
        ("How to transfer money to Senegal?", "montant reçu en FCFA"),
        ("Naka laa mëna yónnee xaalis Senegaal ?", "montant reçu en FCFA"),
        # Dans l'autre sens (FCFA → euros), le coût est un taux au-dessus de la parité.
        ("Comment envoyer de l'argent du Sénégal vers la France ?", "au-dessus de 655,957"),
    ],
)
def test_une_vraie_question_recoit_le_repere(question, phrase):
    assert "envoi_argent" in matching_topics(question)
    assert phrase in practical_context(question)


@pytest.mark.parametrize(
    "question",
    [
        # Payer, retirer, changer : sujet « argent », pas un envoi.
        "Can I pay with my phone in Senegal?",
        "Où retirer de l'argent ? Distributeur ?",
        "Combien vaut 100 dollars en FCFA ?",
        "Où changer des euros à Dakar ?",
        # Envoyer autre chose que de l'argent, ou un transfert qui n'en est pas un.
        "Comment envoyer un colis au Sénégal ?",
        "Envoyer un message WhatsApp gratuit au Sénégal",
        "Le transfert de Sadio Mané, c'est fait ?",
        "Transfert de l'aéroport AIBD à Saly en taxi",
        # « Wise » et « Ria » sont aussi des mots courants.
        "Is it wise to visit Casamance in August?",
        "La plage de Ria à Saly, c'est joli ?",
    ],
)
def test_une_question_voisine_n_ajoute_pas_le_sujet(question):
    assert "envoi_argent" not in matching_topics(question)


def test_le_paragraphe_d_envoi_ne_part_plus_avec_chaque_question_d_argent():
    """Avant, le sujet « argent » portait l'envoi : il partait sur chaque question de paiement ou de distributeur."""
    context = practical_context("Où retirer de l'argent ? Distributeur ?")
    assert "Envoyer de l'argent vers le Sénégal" not in context
    assert "montant reçu en FCFA" not in context


def test_le_sujet_passe_avant_les_sujets_generaux():
    topics = matching_topics("Comment envoyer 200 euros au Sénégal avec Wave ?")
    assert topics.index("envoi_argent") < topics.index("argent")


def test_la_reponse_prete_de_conversion_donne_le_meme_conseil():
    from services.quick_answers import quick_answer

    reply = quick_answer({"message": "100 euros en FCFA ?", "language": "fr"}, {})["reply"]
    assert "comparez le montant reçu, frais compris" in reply
    assert "tout écart entre le taux annoncé et cette parité est un coût" in reply
