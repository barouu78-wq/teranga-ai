"""Repères pratiques : bons sujets détectés, aucun faux déclenchement courant."""

from services.practical_facts import matching_topics, practical_context


def test_topics_detected():
    assert matching_topics("Quels sont les numéros d'urgence ?") == ["urgences"]
    assert "argent" in matching_topics("Combien vaut 100 euros en FCFA ?")
    assert matching_topics("Comment créer une entreprise au Sénégal ?") == ["entreprise"]
    assert matching_topics("Quel type de prise électrique ?") == ["electricite"]
    assert "655,957" in practical_context("100 euros en francs CFA")


def test_no_false_triggers_on_common_phrases():
    for question in ("Une question sur le Sénégal", "Parle-moi de Gorée", "Créer un itinéraire",
                     "Un vol pour Dakar", "Raconte l'histoire de Saint-Louis"):
        assert practical_context(question) == "", question


def test_land_and_selling_topics():
    assert "titre foncier" in practical_context("Je vis en France, comment acheter un terrain au Sénégal ?")
    assert "WhatsApp Business" in practical_context("Comment vendre sur WhatsApp ?")
    for question in ("Construire un itinéraire", "Les clients de mon hôtel"):
        assert "titre foncier" not in practical_context(question) and "WhatsApp Business" not in practical_context(question)



def test_no_false_triggers_inside_words():
    # « visiTER », « goûTER », « FRANCais », « ATMosphère », « HEUREux », « enVISAge », « BUSiness ».
    for question in ("Je veux visiter la Casamance", "Que goûter à Dakar ?", "Je parle français",
                     "Quelle est l'atmosphère à Saint-Louis ?", "Je suis heureux de venir", "J'envisage de venir"):
        assert practical_context(question) == "", question
    assert matching_topics("Comment créer mon business ?") == ["entreprise"]


def test_civil_papers_electricity_social_protection_and_studies_topics():
    assert matching_topics("Comment renouveler ma carte d'identité ?") == ["papiers"]
    assert matching_topics("Je vis en France, comment renouveler mon passeport sénégalais ?") == ["papiers"]
    assert matching_topics("Comment avoir un extrait de naissance ?") == ["papiers"]
    assert matching_topics("Où acheter du crédit Woyofal ?") == ["factures"]
    assert matching_topics("C'est quoi la CMU ?") == ["protection"]
    assert matching_topics("Quelle est la bourse de sécurité familiale ?") == ["protection"]
    assert matching_topics("Comment s'inscrire à Campusen après le bac ?") == ["etudes"]
    assert "orientation.campusen.sn" in practical_context("Campusen, comment ça marche ?")
    assert "trois codes de 20 chiffres" in practical_context("Mon compteur Woyofal demande plusieurs codes")


def test_new_topics_do_not_fire_on_everyday_phrases():
    # « le Sénégal » contient « e Sénégal » (e-Senegal) ; « sécurité familiale » n'est pas une urgence.
    for question in ("Le Sénégal est-il un pays pittoresque ?", "Une question sur le Sénégal", "Parle-moi de Gorée",
                     "Comment aller à l'université Cheikh Anta Diop ?", "Raconte l'histoire de Saint-Louis"):
        context = practical_context(question)
        for marker in ("CEDEAO", "Woyofal", "CMU", "Campusen"):
            assert marker not in context, (question, marker)
    assert "Police 17" not in practical_context("Quelle est la bourse de sécurité familiale ?")


def test_passport_of_a_senegalese_is_not_an_entry_visa_question():
    assert "visa" not in matching_topics("Comment renouveler mon passeport sénégalais ?")
    assert "visa" in matching_topics("Faut-il un visa et un passeport pour le Sénégal ?")
    assert "visa" in matching_topics("Faut-il un passeport pour aller au Sénégal ?")
