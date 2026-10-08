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


def test_foreign_traveller_does_not_get_the_senegalese_papers_procedure():
    assert "papiers" not in matching_topics("J'ai perdu mon passeport français à Dakar")
    assert "papiers" not in matching_topics("My American passport was stolen in Dakar")
    assert "papiers" in matching_topics("Je suis français d'origine sénégalaise, comment renouveler ma carte d'identité sénégalaise ?")


def test_entry_questions_keep_the_visa_facts():
    for question in ("Faut-il refaire mon passeport avant de venir au Sénégal ?",
                     "Comment obtenir un passeport pour aller au Sénégal ?",
                     "Passeport et visa pour un séjour de 10 jours"):
        assert "visa" in matching_topics(question), question


def test_short_acronyms_and_inner_words_do_not_trigger_social_or_paper_topics():
    for question in ("Où apprendre le HTML et le CSS à Dakar ?", "Offre d'emploi directeur DAF"):
        assert matching_topics(question) == [], question
    # « allocations » contient « location » : pas de faits de transport.
    assert matching_topics("Quelles allocations familiales pour mes enfants ?") == ["protection"]
    assert "transport" in matching_topics("Je veux une location de voiture")


def test_specific_topics_are_kept_when_general_words_fill_the_limit():
    topics = matching_topics("Perdu ma carte d'identité à l'aéroport, comment la refaire, payer en euros ?")
    assert topics[0] == "papiers" and len(topics) == 3


def test_demarches_questions_trigger_a_live_web_check():
    from services.web_policy import should_use_web

    for question in ("Comment renouveler ma carte d'identité ?", "Comment avoir un extrait de naissance ?",
                     "Comment recharger mon compteur Woyofal ?", "C'est quoi Campusen ?", "Où faire mon casier judiciaire ?"):
        assert should_use_web(question), question
