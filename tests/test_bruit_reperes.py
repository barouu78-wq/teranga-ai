"""Repères pratiques : des déclencheurs plus étroits, sans perdre la bonne question.

Constat (batterie de questions réalistes, corps de requête identique à celui du site) :
- « sur » (la préposition) ajoutait les numéros d'urgence à « un hôtel à Dakar sur la corniche », alors que
  « Dakar est sûr pour une femme seule ? » n'en recevait aucun ;
- « prise » dans « prise de commande », « location » d'un appartement, « island » (contient « land »),
  « société » (sénégalaise), « heure » d'ouverture, « changé » d'avis ajoutaient des repères hors sujet ;
- le repère « visa » (entrée au Sénégal : « les ressortissants de l'UE n'ont pas besoin de visa ») était donné à un
  Sénégalais qui demande son visa pour l'Espagne ou le Canada : c'est le mauvais sens.

Chaque cas négatif a son cas positif voisin : la bonne question déclenche toujours le bon repère.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import matching_topics, practical_context  # noqa: E402

# (question, sujet attendu)
DECLENCHE = [
    # sécurité : « sûr » au sens de « sans danger »
    ("Est-ce que Dakar est sûr pour une femme seule ?", "urgences"),
    ("Dakar est sûr ?", "urgences"),
    ("Dakar est-il sûr la nuit ?", "urgences"),
    ("Est-ce sûr de marcher la nuit à Dakar ?", "urgences"),
    ("Le Sénégal est-il un pays sûr ?", "urgences"),
    ("Quel quartier est sûr pour loger à Dakar ?", "urgences"),
    ("C'est un endroit sûr pour une famille ?", "urgences"),
    ("Les taxis sont-ils sûrs ?", "urgences"),
    ("Is it safe to walk at night in Dakar?", "urgences"),
    # électricité
    ("Quelle prise électrique au Sénégal ?", "electricite"),
    ("Quel type de prise ?", "electricite"),
    ("Les prises du Sénégal sont-elles compatibles avec la France ?", "electricite"),
    ("Prise de courant au Sénégal", "electricite"),
    # transport
    ("Location de voiture à Dakar", "transport"),
    ("Location de scooter à Saly", "transport"),
    ("car rental in Dakar", "transport"),
    ("Comment aller à Saint-Louis ?", "transport"),
    ("Je veux aller à Gorée", "transport"),
    ("Pour aller à Gorée depuis Dakar", "transport"),
    # visa : entrée au Sénégal
    ("Faut-il un visa pour aller au Sénégal ?", "visa"),
    ("Je suis français, quel visa pour venir au Sénégal ?", "visa"),
    ("Ma femme est française, quel visa pour venir au Sénégal ?", "visa"),
    ("Visa pour le Sénégal depuis la France", "visa"),
    ("Je suis en France, dois-je avoir un visa pour Dakar ?", "visa"),
    ("Je vis en France, quels papiers pour voyager au Sénégal avec mon fils ?", "visa"),
    ("Do I need a visa for Senegal as a US citizen?", "visa"),
    ("Faut-il un visa pour un Français ?", "visa"),
    ("Je suis français, je veux voyager au Sénégal en décembre, il faut quoi comme papiers ?", "visa"),
    # foncier
    ("Je veux acheter un terrain à Diamniadio", "foncier"),
    ("Is it safe to buy land in Senegal?", "foncier"),
    # entreprise
    ("Comment créer une société au Sénégal ?", "entreprise"),
    ("SARL ou société anonyme ?", "entreprise"),
    # heure
    ("Quel est le décalage horaire avec Paris ?", "heure"),
    ("Quelle heure est-il à Dakar ?", "heure"),
    ("Il est quelle heure au Sénégal ?", "heure"),
    ("What time is it in Dakar?", "heure"),
    # argent
    ("Où changer mes euros à Dakar ?", "argent"),
    ("Quel est le taux de change euro FCFA ?", "argent"),
    ("Bureau de change à l'AIBD", "argent"),
    ("Quel est le change aujourd'hui ?", "argent"),
    ("Where can I change money at the airport?", "argent"),
    # vente
    ("Comment vendre sur WhatsApp ?", "vente"),
    ("Prise de commande par WhatsApp pour mes clients", "vente"),
    ("Comment fixer mon prix de vente ?", "vente"),
]

# (question, sujet qui ne doit PAS être ajouté)
NE_DECLENCHE_PAS = [
    # « sur » préposition
    ("Saint-Louis, ville sur le fleuve, que voir ?", "urgences"),
    ("Hôtels à Dakar sur la corniche", "urgences"),
    ("Je cherche un appartement à Dakar sur Mermoz", "urgences"),
    ("Un endroit sur Dakar pour déjeuner", "urgences"),
    ("Le Sénégal sur la carte de l'Afrique", "urgences"),
    ("Dakar sur Google Maps", "urgences"),
    ("Mon hôtel est sur la plage", "urgences"),
    ("Un pays sur lequel investir", "urgences"),
    ("Vols Paris Dakar sur Air Sénégal", "urgences"),
    ("Mon quartier sur la VDN est bruyant", "urgences"),
    # « prise » dans un autre sens
    ("Prise de commande par WhatsApp pour mes clients", "electricite"),
    ("La prise en charge médicale à Dakar", "electricite"),
    ("Une prise de sang à Dakar", "electricite"),
    ("Prise de rendez-vous pour le passeport", "electricite"),
    ("La prise d'otage de la semaine dernière", "electricite"),
    # « location » d'un logement ou d'une salle
    ("Prix d'une location d'appartement à Dakar", "transport"),
    ("Je cherche une location de salle pour un mariage", "transport"),
    ("Location saisonnière à Saly", "transport"),
    # aller à l'étranger
    ("Quel visa pour un Sénégalais qui veut aller au Canada ?", "transport"),
    ("Je veux aller en France, quels papiers ?", "transport"),
    # visa dans l'autre sens : un Sénégalais qui voyage
    ("Un Sénégalais peut aller en France sans visa ?", "visa"),
    ("Mon cousin sénégalais veut un visa pour l'Espagne, quels documents ?", "visa"),
    ("Je suis sénégalais et je voyage au Maroc, il faut un visa ?", "visa"),
    ("Quel visa pour un Sénégalais qui veut aller au Canada ?", "visa"),
    ("I am Senegalese, how do I get a visa for the UK?", "visa"),
    ("Comment obtenir un visa Schengen depuis Dakar ?", "visa"),
    ("Quel visa pour la France depuis le Sénégal ?", "visa"),
    # « land » dans « island », terrains de sport
    ("Tell me about Goree island", "foncier"),
    ("Island hopping in the Saloum delta", "foncier"),
    ("Terrain de foot à Dakar", "foncier"),
    ("Terrain de basket à Pikine", "foncier"),
    # « société » au sens de la vie en société
    ("Parle-moi de la société sénégalaise", "entreprise"),
    ("Quelle est la place de la femme dans la société wolof ?", "entreprise"),
    ("Société Générale Sénégal : où est l'agence ?", "entreprise"),
    # « heure » d'ouverture, de vol, de prière
    ("Les heures d'ouverture du marché Kermel", "heure"),
    ("Combien d'heures de vol Paris Dakar ?", "heure"),
    ("À quelle heure part le ferry pour Gorée ?", "heure"),
    ("Heure de prière à Dakar", "heure"),
    ("Combien d'heures de route jusqu'à Touba ?", "heure"),
    # « change » : changer d'avis, de numéro
    ("J'ai changé d'avis", "argent"),
    ("Ça change quoi pour moi ?", "argent"),
    ("Je veux changer de numéro", "argent"),
    ("Convertir un fichier PDF", "argent"),
    # WhatsApp hors commerce, vente d'un bien
    ("Numéro WhatsApp de l'ambassade", "vente"),
    ("Mon groupe WhatsApp de famille", "vente"),
    ("Comment vendre ma maison à Saly ?", "vente"),
    ("Comment vendre ma voiture ?", "vente"),
]


@pytest.mark.parametrize("question,sujet", DECLENCHE, ids=[q for q, _ in DECLENCHE])
def test_la_bonne_question_declenche_le_bon_repere(question, sujet):
    assert sujet in matching_topics(question), (question, matching_topics(question))


@pytest.mark.parametrize("question,sujet", NE_DECLENCHE_PAS, ids=[q for q, _ in NE_DECLENCHE_PAS])
def test_une_question_voisine_n_ajoute_pas_le_repere(question, sujet):
    assert sujet not in matching_topics(question), (question, matching_topics(question))


def test_le_repere_visa_d_entree_n_est_jamais_donne_a_un_senegalais_qui_part():
    for question in ("Un Sénégalais peut aller en France sans visa ?", "Quel visa pour un Sénégalais qui veut aller au Canada ?"):
        contexte = practical_context(question)
        assert "ressortissants de l'Union européenne" not in contexte, question
    assert "ressortissants de l'Union européenne" in practical_context("Faut-il un visa pour aller au Sénégal ?")


def test_aucune_urgence_pour_un_hotel_sur_la_corniche():
    assert practical_context("Hôtels à Dakar sur la corniche") == ""
    assert "Police 17" in practical_context("Est-ce que Dakar est sûr pour une femme seule ?")
