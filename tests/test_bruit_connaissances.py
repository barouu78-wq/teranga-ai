"""Base de connaissances : personnalités, lieux et régions hors sujet.

Constat (batterie de questions réalistes) : 46 questions sur 78 recevaient des biographies sans rapport, dont
celle de Djibril Tamsir Niane (et sa consigne de style de 120 à 180 mots) pour « un thieb pas cher » ou « refaire
ma carte d'identité » : la recherche d'une personne comparait la question à des morceaux de mots
(« cher » dans « chercheur », « hier » dans « hiérarchie », « identité » dans une consigne de style). De même,
« ça marche » faisait remonter les marchés, « visite guidée » le parc du Niokolo-Koba, et un plat cité avec une
ville ajoutait quatre régions.

Chaque cas négatif a son cas positif voisin : la personne, le lieu ou la région demandés sont toujours là.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge, load_senegal_people  # noqa: E402

DATA = load_senegal_knowledge()
PEOPLE = load_senegal_people()


def contexte(question):
    return format_senegal_knowledge(DATA, query=question, people=PEOPLE)


def _noms(question, titre):
    """Noms des entrées de la section « titre » : les lignes « - Nom: ... » qui suivent son intitulé."""
    texte = contexte(question)
    if titre + " :" not in texte:
        return []
    noms = []
    for ligne in texte.split(titre + " :")[1].split("\n")[1:]:
        if not ligne.startswith("- "):
            break
        noms.append(ligne[2:].split(":")[0])
    return noms


def lieux(question):
    return _noms(question, "LIEUX PERTINENTS")


def regions(question):
    return _noms(question, "CONTEXTE RÉGIONAL PERTINENT")


SANS_PERSONNE = [
    "Je veux manger du thieb pas cher",
    "Comment refaire ma carte d'identité ?",
    "Mon fils a de la fièvre depuis hier",
    "Quel temps fait-il demain à Dakar ?",
    "Quel est le taux de change dollar FCFA ?",
    "Où acheter des souvenirs à Dakar ?",
    "What is the best area to stay in Dakar?",
    "Combien coûte un taxi de l'aéroport à Dakar ?",
    "Quels documents pour inscrire mon fils à l'école ?",
    "Je rentre au pays pour la Tabaski, conseils ?",
    "Comment renouveler mon passeport sénégalais à Paris ?",
]


@pytest.mark.parametrize("question", SANS_PERSONNE)
def test_une_question_pratique_n_injecte_aucune_biographie(question):
    texte = contexte(question)
    assert "PERSONNALITÉS PERTINENTES" not in texte, question
    assert "Niane" not in texte, question


@pytest.mark.parametrize("question", ["Je veux manger du thieb pas cher", "Comment refaire ma carte d'identité ?"])
def test_la_consigne_de_style_de_niane_ne_part_pas_sans_lui(question):
    assert "Pour une biographie demandée explicitement" not in contexte(question)


@pytest.mark.parametrize("question,attendu", [
    ("Qui est Djibril Tamsir Niane ?", "Djibril Tamsir Niane"),
    ("Parle-moi de Niane, l'historien", "Djibril Tamsir Niane"),
    ("Qui était Seydina Limamou Laye ?", "Seydina Limamou Laye"),
    ("Parle-moi de Youssou Ndour", "Youssou Ndour"),
    # personne retrouvée par un mot rare de sa fiche, pas par son nom
    ("Qui a écrit Une si longue lettre ?", "Mariama Bâ"),
    ("Qui a fondé la confrérie layène à Yoff ?", "Seydina Limamou Laye"),
    ("Qui a fondé la ville de Touba ?", "Cheikh Ahmadou Bamba Mbacké"),
    ("Qui a écrit Les Bouts de bois de Dieu ?", "Ousmane Sembène"),
])
def test_la_personne_demandee_est_toujours_la(question, attendu):
    texte = contexte(question)
    assert "PERSONNALITÉS PERTINENTES" in texte and attendu in texte.split("PERSONNALITÉS PERTINENTES")[1], question


def test_la_consigne_de_style_de_niane_part_quand_on_parle_de_lui():
    assert "Pour une biographie demandée explicitement" in contexte("Qui est Djibril Tamsir Niane ?")


@pytest.mark.parametrize("question", [
    "Mon compteur Woyofal ne marche pas",
    "Wave marche pour les touristes ?",
    "Jërëjëf, ça marche",
    "Ça ne marche plus depuis hier",
])
def test_le_verbe_marcher_ne_fait_pas_remonter_les_marches(question):
    assert not any(nom.startswith("Marché") for nom in lieux(question)), question
    assert "Kolda" not in regions(question), question


@pytest.mark.parametrize("question,attendu", [
    ("Où se trouve le marché Sandaga ?", "Marché Sandaga"),
    ("Horaires du marché Kermel", "Marché Kermel"),
    ("Quels sont les marchés de Dakar ?", "Marché Sandaga"),
    ("Le marché hebdomadaire de Diaobé", "Marché hebdomadaire de Diaobé"),
])
def test_le_nom_marche_retrouve_toujours_les_marches(question, attendu):
    assert attendu in lieux(question), question


def test_visite_guidee_ne_fait_pas_remonter_les_parcs_ou_le_mot_guide_apparait():
    noms = lieux("Salut je cherche une visite guidée de Gorée")
    assert noms[0] == "Île de Gorée"
    assert "Parc national du Niokolo-Koba" not in noms and "Cascades de Dindéfello" not in noms


@pytest.mark.parametrize("question", [
    "Mon fils a de la fièvre depuis hier",
    "Mon quartier n'a pas d'eau depuis 3 jours, qui appeler ?",
    "Comment renouveler mon passeport sénégalais à Paris ?",
    "Ma femme est française, quel visa pour venir au Sénégal ?",
    "Quelle carte SIM acheter pour une femme seule ?",
])
def test_des_mots_courants_ne_designent_aucun_lieu(question):
    assert lieux(question) == [], question


def test_un_lieu_nomme_ne_ramene_pas_les_lieux_qui_partagent_un_seul_mot():
    # Gorée est nommé : un lieu qui ne le cite qu'en passant, ou qui partage « nuit » avec la question, n'est pas demandé.
    assert lieux("Parle-moi de Gorée")[0] == "Île de Gorée" and "Vieux Rufisque" not in lieux("Parle-moi de Gorée")
    assert lieux("Combien coûte une nuit à Saly ?")[0] == "Saly" and "Ziguinchor" not in lieux("Combien coûte une nuit à Saly ?")
    # Deux lieux nommés restent tous les deux, et une question sans lieu nommé garde tous les lieux trouvés.
    assert {"Saly", "Mbour"} <= set(lieux("Que voir à Saly et à Mbour ?"))
    assert len(lieux("Que faire en Casamance ?")) >= 3


def test_les_souvenirs_ne_designent_pas_la_cathedrale_du_souvenir_africain():
    assert "Cathédrale du Souvenir africain" not in lieux("Quels souvenirs rapporter du Sénégal ?")
    assert "Cathédrale du Souvenir africain" in lieux("Où se trouve la Cathédrale du Souvenir africain ?")


def test_profil_du_pays_et_numeros_d_urgence_seulement_pour_leur_sujet():
    # « prise de commande », « prise en charge » ne sont pas une prise électrique ; « volet » n'est pas un vol.
    for question in ("Prise de commande par WhatsApp pour mes clients", "Une prise de sang à Dakar", "La prise en charge médicale"):
        assert "Profil : superficie" not in contexte(question), question
    assert "Profil : superficie" in contexte("Quel type de prise électrique au Sénégal ?")
    assert "Profil : superficie" in contexte("Quelle prise de courant au Sénégal ?")
    assert "Numéros d'urgence au Sénégal" not in contexte("Le volet de ma fenêtre est cassé")
    for question in ("On m'a volé mon sac", "Je me suis fait voler mon téléphone", "Un voleur est entré chez moi"):
        assert "Numéros d'urgence au Sénégal" in contexte(question), question


def test_un_plat_cite_avec_une_ville_ne_donne_que_la_region_de_la_ville():
    assert regions("Meilleur resto de poisson à Saint-Louis") == ["Saint-Louis"]
    assert regions("Où manger du thiéboudienne à Saint-Louis ?") == ["Saint-Louis"]


def test_deux_lieux_de_deux_regions_gardent_leurs_deux_regions():
    noms = regions("Parle-moi de Touba et de Saint-Louis")
    assert "Saint-Louis" in noms and "Diourbel" in noms


def test_une_question_sans_region_nommee_garde_les_regions_trouvees_par_theme():
    noms = regions("Que faire en Casamance ?")
    assert "Ziguinchor" in noms
