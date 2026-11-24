"""Sujet « frontieres » (services/facts/frontieres.py) : passer une frontière terrestre vers un pays voisin."""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import matching_topics, practical_context  # noqa: E402


@pytest.mark.parametrize(
    ("question", "phrase"),
    [
        ("Comment aller en Casamance en voiture par la Gambie ?", "pont de Farafenni"),
        ("Comment aller en Casamance en voiture par la Gambie ?", "papiers valables pour la Gambie"),
        ("Faut-il changer de l'argent pour aller à Banjul ?", "n'a pas forcément cours"),
        ("Je vais à Nouakchott par Rosso, quels papiers ?", "ambassade ou du consulat du pays voisin"),
        ("Est-ce que je peux aller au Mali en bus depuis Dakar ?", "conseils aux voyageurs officiels"),
        ("Ma puce Orange marche en Guinée-Bissau si je pars à Bissau ?", "itinérance"),
        ("Voiture de location pour aller en Mauritanie, c'est possible ?", "accord écrit du loueur"),
        ("Can I drive from Dakar to Banjul?", "poste frontière officiel"),
        ("Comment passer la frontière à Rosso ?", "poste frontière officiel"),
    ],
)
def test_une_vraie_question_recoit_le_repere(question, phrase):
    assert "frontieres" in matching_topics(question)
    assert phrase in practical_context(question)


@pytest.mark.parametrize(
    "question",
    [
        # Le fleuve et la rivière Gambie traversent le Niokolo-Koba : ce n'est pas un passage de frontière.
        "Aller voir les hippopotames du fleuve Gambie au Niokolo-Koba",
        "Visiter la rivière Gambie en pirogue près de Kédougou",
        # Histoire et culture : un pays voisin cité sans voyage.
        "Raconte-moi l'histoire de l'empire du Mali et de Soundiata",
        "Les Peuls vivent au Sénégal, en Mauritanie et au Mali",
        "Le thiéboudienne existe aussi en Gambie ?",
        "Quelle est la capitale de la Mauritanie ?",
        "Visiter les cercles mégalithiques de Sénégambie",
        # Autres « Guinée » et « frontières ».
        "Voyager dans le golfe de Guinée en bateau",
        "Médecins sans frontières est présent à Dakar ?",
        "Je cherche un restaurant guinéen à Dakar",
        # « Malien » n'est pas « Mali » : un Malien qui vient au Sénégal relève du sujet visa.
        "Un Malien a-t-il besoin d'un visa pour venir au Sénégal ?",
        # Dakar est sur la presqu'île du Cap-Vert : ce n'est pas l'archipel.
        "Aller sur la presqu'île du Cap-Vert à Dakar",
        "Je pars en vacances à Saly, c'est loin de Dakar ?",
    ],
)
def test_une_question_voisine_n_ajoute_pas_le_sujet(question):
    assert "frontieres" not in matching_topics(question)


def test_le_sujet_passe_avant_les_sujets_generaux():
    """« Argent » seul dirait le franc CFA du Sénégal : le repère frontière passe d'abord et dit de vérifier."""
    topics = matching_topics("Faut-il changer de l'argent pour aller à Banjul ?")
    assert topics[0] == "frontieres"
    assert "argent" in topics


def test_le_visa_d_entree_au_senegal_reste_retire_pour_un_pays_voisin():
    topics = matching_topics("Visa pour la Mauritanie ?")
    assert "visa" not in topics
    assert "frontieres" in topics


def test_un_malien_qui_vient_par_la_route_recoit_le_repere():
    assert "frontieres" in matching_topics("Je suis Malien et je viens à Dakar par la route depuis Bamako")


def test_aucun_fait_du_pays_voisin_n_est_affirme():
    """Pas de monnaie, de poste ni de pièce exigée par un pays voisin tant qu'une page officielle n'a pas été lue."""
    texte = practical_context("Comment passer la frontière à Rosso ?")
    for mot in ("dalasi", "ouguiya", "franc guinéen", "laissez-passer", "carte brune", "gratuit", "obligatoire"):
        assert mot not in texte.lower(), mot
