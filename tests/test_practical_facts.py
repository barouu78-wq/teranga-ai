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


# --- Premiers secours : sujet sensible, repères généraux sans dose ni diagnostic ---------------------------------

FIRST_AID_QUESTIONS = (
    "Quels sont les symptômes du paludisme ?",
    "Comment éviter le paludisme au Sénégal ?",
    "Faut-il une moustiquaire ?",
    "Quel répulsif anti-moustiques utiliser à Saly ?",
    "Mon enfant a de la fièvre, que faire ?",
    "Mon bébé est malade, que faire ?",
    "Mon fils a fait une convulsion",
    "Comment éviter la déshydratation avec la chaleur ?",
    "Qu'est-ce qu'un coup de chaleur ?",
    "J'ai la diarrhée depuis hier",
    "J'ai la tourista, que faire ?",
    "Mon enfant vomit depuis ce matin",
    "Un chien m'a mordu à Dakar",
    "Morsure de serpent : que faire ?",
    "Y a-t-il des serpents dangereux au Sénégal ?",
    "Piqûre de scorpion que faire ?",
    "J'ai été piqué par une guêpe",
    "Je me suis brûlé la main",
    "Je me suis coupé profondément",
    "Peut-on boire l'eau du robinet ?",
    "L'eau est-elle potable à Saint-Louis ?",
    "Faut-il éviter les glaçons ?",
    "Est-ce dangereux de manger dans la rue ?",
    "J'ai peut-être une intoxication alimentaire",
    "Quels sont les premiers secours en cas de malaise ?",
    "Y a-t-il des risques de rage au Sénégal ?",
    "Is the tap water safe to drink in Senegal?",
    "My child has a fever, what should I do?",
    "What are the symptoms of malaria?",
    "How to avoid dehydration in the heat?",
    "A dog bit me in Dakar",
)

# Questions voisines qui ne doivent pas faire apparaître le sujet : mots qui en contiennent d'autres
# (« coupure » de courant, « rage » de dents, « piquant », « mordu » de football), fièvre jaune, accès à l'eau.
FIRST_AID_NOISE = (
    "Quels sont les numéros d'urgence ?",
    "Faut-il un vaccin contre la fièvre jaune ?",
    "Faut-il un vaccin pour aller au Sénégal ?",
    "Une piqûre de rappel pour la fièvre jaune ?",
    "Où trouver une pharmacie de garde à Dakar ?",
    "Il y a eu une coupure de courant à Dakar",
    "Coupure d'électricité : comment recharger mon compteur Woyofal ?",
    "Quel est le plat le plus piquant ?",
    "Un pique-nique à Saly",
    "Je suis un mordu de football, quel match voir ?",
    "Le poisson a mordu à Joal",
    "J'ai une rage de dents",
    "Il est fou de rage",
    "Je suis en rage contre cette administration",
    "Qu'est-ce que le riz brûlé dans la cuisine sénégalaise ?",
    "Quel est le taux d'accès à l'eau potable au Sénégal ?",
    "Qu'est-ce que la gastronomie sénégalaise ?",
    "Quelle est la coupe du monde 2026 ?",
    "Où manger du thiéboudienne à Dakar ?",
    "Quels plats manger à Saint-Louis ?",
    "Risque d'inondation à Dakar en saison des pluies",
    "Mon fils veut visiter Gorée",
    "It is a bit expensive",
    "La chaleur à Tambacounda en avril",
    "Quelle est la meilleure période pour visiter le Sénégal ?",
)


def test_first_aid_topic_is_detected():
    for question in FIRST_AID_QUESTIONS:
        assert "premiers_secours" in matching_topics(question), question


def test_first_aid_topic_has_no_false_triggers():
    for question in FIRST_AID_NOISE:
        assert "premiers_secours" not in matching_topics(question), question
        assert "Cadre : repères généraux" not in practical_context(question), question


def test_first_aid_topic_completes_health_and_emergency_topics():
    # La fièvre reste une question d'urgence (numéros) ; le paludisme et l'eau restent des questions de santé.
    assert matching_topics("Mon enfant a de la fièvre à Dakar, que faire ?") == ["premiers_secours", "urgences"]
    assert matching_topics("Quels sont les symptômes du paludisme ?") == ["premiers_secours", "sante"]
    assert matching_topics("On peut boire l'eau du robinet ?") == ["premiers_secours", "sante"]
    # Questions de santé sans premiers secours : le sujet ne s'ajoute pas.
    assert matching_topics("Où trouver une pharmacie de garde à Dakar ?") == ["sante"]
    assert matching_topics("Quels sont les numéros d'urgence ?") == ["urgences"]
    # Le vaccin de la fièvre jaune relève de « sante », pas des premiers secours.
    assert "premiers_secours" not in matching_topics("Faut-il le vaccin contre la fièvre jaune ?")
    # Une morsure seule n'appelle ni les numéros ni les repères de santé du voyageur.
    assert matching_topics("Un chien m'a mordu, que faire ?") == ["premiers_secours"]


def test_first_aid_topic_survives_the_limit_of_three_topics():
    # La couverture maladie, l'urgence et la santé fournissent déjà trois sujets : les premiers secours passent devant.
    topics = matching_topics("À l'hôpital en urgence pour un paludisme, la CMU couvre-t-elle les frais ?")
    assert len(topics) == 3 and topics[0] == "premiers_secours" and "protection" in topics
    topics = matching_topics("J'ai de la fièvre et la diarrhée, comment payer le médecin en euros et aller à l'hôpital en taxi ?")
    assert len(topics) == 3 and topics[0] == "premiers_secours"


def _first_aid_facts():
    from services.practical_facts import TOPICS

    return dict((name, facts) for name, _, facts in TOPICS)["premiers_secours"]


def test_first_aid_topic_is_placed_right_after_health():
    from services.practical_facts import TOPICS

    names = [name for name, _, _ in TOPICS]
    assert names.index("premiers_secours") == names.index("sante") + 1


def test_every_first_aid_fact_points_to_a_professional_or_the_samu():
    facts = _first_aid_facts()
    assert len(facts) >= 10
    for fact in facts:
        folded = fact.casefold()
        assert "samu 1515" in folded or "professionnel de santé" in folded or "médecin" in folded, fact


def test_first_aid_topic_gives_no_dose_no_drug_name_and_no_other_phone_number():
    import re

    text = " ".join(_first_aid_facts())
    folded = text.casefold()
    # Aucune posologie : ni unité de dose, ni forme galénique, ni médicament nommé.
    assert not re.search(r"\d\s*(mg|µg|g|ml|cl|l)\b", folded)
    for word in ("comprimé", "gélule", "goutte", "sachet", "cuillère", "posologie", "paracétamol", "ibuprofène",
                 "aspirine", "artémisinine", "chloroquine", "doxycycline", "atovaquone", "méfloquine", "antibiotique"):
        assert word not in folded, word
    # Aucun numéro de téléphone hors des numéros nationaux déjà vérifiés (SAMU 1515, police 17, pompiers 18).
    numbers = set(re.findall(r"\d{3,}", text))
    assert numbers == {"1515"}, numbers
    assert "Police 17" in text and "pompiers 18" in text


def test_first_aid_topic_keeps_the_sensitive_warnings():
    context = practical_context("Mon enfant a de la fièvre, je pense à un palu : que faire ?")
    for phrase in (
        "ne remplacent pas un professionnel de santé",
        "aucun diagnostic",
        "aucune dose de médicament",
        "SAMU 1515",
        "ne se soigne jamais sans avis médical",
        "signes généraux de danger de l'OMS",
    ):
        assert phrase in context, phrase


def test_first_aid_questions_trigger_a_live_web_check():
    from services.web_policy import should_use_web

    for question in ("Quels sont les symptômes du paludisme ?", "Mon enfant a de la fièvre", "Comment éviter la déshydratation ?",
                     "Que faire en cas de morsure de serpent ?", "Premiers secours pour une brûlure", "J'ai la diarrhée",
                     "Quelle moustiquaire acheter ?", "Piqûre de scorpion : que faire ?"):
        assert should_use_web(question), question


def test_first_aid_words_are_listed_with_and_without_accents_in_the_web_policy():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "services" / "web_policy.py").read_text(encoding="utf-8")
    for accented, plain in (("fièvre", "fievre"), ("répulsif", "repulsif"), ("déshydratation", "deshydratation"),
                            ("diarrhée", "diarrhee"), ("piqûre", "piqure"), ("brûlure", "brulure")):
        assert f'"{accented}"' in source and f'"{plain}"' in source, (accented, plain)
