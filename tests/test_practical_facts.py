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


def test_scam_topic_is_detected_in_real_questions():
    for question in ("Quelles arnaques à éviter à Dakar pour un touriste ?",
                     "On m'a demandé un code reçu par SMS, c'est une arnaque ?",
                     "Comment reconnaître un faux billet de 10 000 FCFA ?",
                     "Un faux policier m'a demandé de l'argent",
                     "J'ai reçu un SMS d'amende avec un lien de paiement",
                     "Un intermédiaire me promet un visa contre de l'argent",
                     "Un faux recruteur me demande de payer pour un emploi en Europe",
                     "Comment louer un appartement à Dakar à distance ?",
                     "On me demande un acompte avant la visite de l'appartement",
                     "Mon frère m'écrit d'un nouveau numéro et demande de l'argent en urgence",
                     "Mon compte WhatsApp a été piraté",
                     "Common scams for tourists in Senegal"):
        assert "arnaques" in matching_topics(question), question
    assert "carte professionnelle" in practical_context("Un faux policier m'a arrêté, que faire ?")


def test_mobile_money_topic_is_detected_in_real_questions():
    for question in ("Comment fonctionne Wave ?", "C'est quoi Orange Money ?", "C'est quoi Free Money ?",
                     "Comment protéger mon code secret Orange Money ?",
                     "J'ai envoyé de l'argent au mauvais numéro",
                     "Quelqu'un dit m'avoir envoyé de l'argent par erreur et me demande de le renvoyer",
                     "Comment payer avec Wave à Ngor ?", "Où se plaindre contre un opérateur de mobile money ?"):
        assert "mobile_money" in matching_topics(question), question
    assert "Free Sénégal est devenu Yas" in practical_context("Comment fonctionne Free Money ?")


def test_scam_and_mobile_money_topics_do_not_fire_on_everyday_phrases():
    # « vol » dans « volontaire », film ou série intitulés « Arnaque », billet d'avion, fraude électorale ou fiscale,
    # code postal, tirage au sort, vague de surf, opérateur de réseau sans argent mobile.
    for question in ("Qui joue dans le film L'Arnaque avec Paul Newman ?",
                     "Que penser de la série Netflix sur une arnaque financière ?",
                     "Je suis volontaire pour une ONG au Sénégal", "Je cherche un billet d'avion pour Dakar",
                     "Y a-t-il de la fraude électorale au Sénégal ?", "Je m'intéresse à la fraude fiscale au Sénégal",
                     "Quel est le code postal de Dakar ?", "Comment fonctionne le tirage au sort de la CAN ?",
                     "Peut-on louer un appartement à Dakar pour un mois ?", "J'ai trouvé une annonce pour louer une maison à Saly",
                     "Où trouver un logement avant la visite de Saint-Louis ?",
                     "Quel est le meilleur moment pour surfer la vague de Ngor ?",
                     "Mon opérateur Orange a-t-il du réseau à Kédougou ?", "Comment faire un virement vers la France ?"):
        topics = matching_topics(question)
        assert "arnaques" not in topics and "mobile_money" not in topics, (question, topics)
    # Wave seul, au sens de la vague de surf : le sujet argent mobile n'est pas ajouté ; avec un mot d'argent, il l'est.
    assert "mobile_money" not in matching_topics("Le surf à Ngor : la wave est-elle bonne en novembre ?")
    assert "mobile_money" in matching_topics("Le surf à Ngor est sympa, mais puis-je payer avec Wave ?")
    # Une question qui parle réellement de fraude garde le sujet même si elle cite un film.
    assert "arnaques" in matching_topics("Après le film, j'ai reçu un SMS avec un code secret demandé par un faux agent")


def test_scam_and_mobile_money_topics_come_before_general_ones_when_the_limit_cuts():
    topics = matching_topics("Un faux policier m'a arrêté à l'aéroport en taxi, j'ai payé en euros via Wave")
    assert topics[:2] == ["arnaques", "mobile_money"] and len(topics) == 3
    assert matching_topics("Fraude au mobile money, que faire ?")[:2] == ["arnaques", "mobile_money"]


def test_scam_and_mobile_money_facts_cite_no_amount_phone_number_or_named_culprit():
    import re

    from services.practical_facts import TOPICS

    for name, _, facts in TOPICS:
        if name not in ("arnaques", "mobile_money"):
            continue
        text = " ".join(facts)
        assert "FCFA" not in text and "%" not in text, name
        # Aucun numéro de téléphone ni montant : seuls le 17 de la police et des années sont autorisés.
        assert not re.search(r"\d{3,}\s?\d{2,}|\b\d{1,3}(?:[ .]\d{3})+\b", text), name
        assert not re.search(r"\b(?!20\d\d\b)\d{3,}\b", text), name
        # Ni site, ni entreprise, ni personne désignés comme fraudeurs : seulement des mécanismes et des réflexes.
        for forbidden in ("Senevisa", "Sonatel", "Wave Mobile Money", "amendes-sn", "http"):
            assert forbidden not in text, (name, forbidden)
        assert "à vérifier" in text or "se vérifient" in text or "vérifier" in text, name


def test_scam_and_mobile_money_questions_trigger_a_live_web_check():
    from services.web_policy import should_use_web

    for question in ("Quelles arnaques à éviter à Dakar ?", "C'est une escroquerie ce message ?",
                     "Comment reconnaître un faux billet ?", "Qu'est-ce que le hameçonnage ?",
                     "Où faire une réclamation contre mon opérateur ?", "Fraude au mobile money, que faire ?",
                     "Quelqu'un me demande mon code secret", "Un faux visa m'a été proposé", "C'est quoi Yas Money ?"):
        assert should_use_web(question), question
    for question in ("Quelle est la capitale du Sénégal ?", "Qui est Léopold Sédar Senghor ?"):
        assert not should_use_web(question), question


def test_demarches_questions_trigger_a_live_web_check():
    from services.web_policy import should_use_web

    for question in ("Comment renouveler ma carte d'identité ?", "Comment avoir un extrait de naissance ?",
                     "Comment recharger mon compteur Woyofal ?", "C'est quoi Campusen ?", "Où faire mon casier judiciaire ?"):
        assert should_use_web(question), question
