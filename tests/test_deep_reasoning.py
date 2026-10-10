"""Raisonnement approfondi : réservé aux vraies demandes complexes, pas à toute question qui contient « pourquoi ».

`should_use_deep_reasoning` envoie la question au modèle complexe (plus lent, plus cher, hors cache). Avant, un
mot comme « pourquoi », « comment faire », « plan », « organise », « quel est le meilleur » ou « priorité » suffisait,
et « ce soir » + « demain » comptaient pour deux contraintes.

Deux corpus de questions réalistes (touristes, résidents, diaspora, commerçants), étiquetés AVANT la mesure :
- `MESURE` a servi à écrire la règle ; `HORS_ECHANTILLON` a été écrit après, pour vérifier qu'elle ne colle pas
  seulement aux exemples.
Mesure sur `main` : 30 questions simples sur 39 (la limite connue ci-dessous comprise) partaient en raisonnement
approfondi, et 4 vraies demandes complexes sur 26 n'y allaient pas (« étapes », « priorités », « organiser » et
« comparer » à l'infinitif ou au pluriel). Après : 1 simple sur 39 (la limite connue), 26 complexes sur 26.
Les corps de requête reproduisent static/home.js (la question courante est déjà le dernier élément de ``history``).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

import app as app_module
from services.answer_cache import cache_key
from services.intelligence import should_use_deep_reasoning

FAST_MODEL = "gpt-5.6-luna"
COMPLEX_MODEL = "gpt-5.6-sol"

# (profil, question) : raisonnement approfondi INUTILE.
SIMPLES_MESURE = [
    ("touriste", "Pourquoi le lac Rose est-il rose ?"),
    ("touriste", "Pourquoi les taxis de Dakar sont-ils jaunes et noirs ?"),
    ("touriste", "Pourquoi dit-on que le Sénégal est le pays de la teranga ?"),
    ("touriste", "Où trouver un plan de Dakar ?"),
    ("touriste", "Comment faire pour dire bonjour en wolof ?"),
    ("touriste", "Quel est le meilleur moment pour visiter Gorée ?"),
    ("touriste", "Quel est le meilleur restaurant de thiéboudienne à Dakar ?"),
    ("touriste", "Que veut dire teranga ?"),
    ("touriste", "Où dîner ce soir à Dakar et que faire demain ?"),
    ("résident", "Pourquoi y a-t-il des coupures d'électricité à Dakar ?"),
    ("résident", "Comment faire pour recharger mon compteur Woyofal ?"),
    ("résident", "Qui organise le Grand Magal de Touba ?"),
    ("résident", "Quel est le numéro de la police ?"),
    ("résident", "Pourquoi mon forfait internet est-il si lent le soir ?"),
    ("résident", "Où acheter une carte SIM à Dakar ?"),
    ("résident", "Y a-t-il un marché ce soir, et la pharmacie ouvre-t-elle demain ?"),
    ("résident", "Quelle est la priorité à un rond-point à Dakar ?"),
    ("diaspora", "Comment envoyer de l'argent au Sénégal depuis la France ?"),
    ("diaspora", "Pourquoi mon transfert Wave n'est-il pas arrivé ?"),
    ("diaspora", "Quelle est la date de la Tabaski cette année ?"),
    ("diaspora", "Comment faire pour faire venir un colis du Sénégal ?"),
    ("diaspora", "Pourquoi les billets d'avion sont chers en août ?"),
    ("commerçant", "Combien coûte un étal au marché Sandaga ?"),
    ("commerçant", "Comment faire un prix de vente pour mes jus de bissap ?"),
    ("commerçant", "Comment dit-on « combien ça coûte » en wolof ?"),
    ("commerçant", "Où acheter des sacs en gros à Dakar ?"),
]

# (profil, question) : raisonnement approfondi UTILE (plans chiffrés, comparaisons, démarches à étapes).
COMPLEXES_MESURE = [
    ("touriste", "Prépare-moi un séjour de 7 jours entre Dakar, Saint-Louis et la Casamance avec 1 200 000 FCFA pour 4 personnes"),
    ("touriste", "Compare Saly et Somone pour des vacances en famille avec 2 enfants"),
    ("touriste", "Quels sont les avantages et inconvénients de louer une voiture ou de prendre des taxis pour un séjour de 10 jours ?"),
    ("touriste", "Organise une semaine entre Dakar et le Sine-Saloum avec un budget de 500000 FCFA"),
    ("touriste", "Peux-tu comparer Saly et Somone pour une famille ?"),
    ("touriste", "Quel est le meilleur choix entre le bus et le taxi pour aller à Saint-Louis ?"),
    ("résident", "Quelles sont les étapes pour créer une SARL au Sénégal, avec les coûts et les délais ?"),
    ("résident", "Je dois choisir entre louer ou acheter un appartement à Dakar avec 25 millions de FCFA, que me conseilles-tu ?"),
    ("résident", "Comment faire pour obtenir un acte de naissance, un passeport et une carte d'identité depuis l'étranger, dans quel ordre ?"),
    ("diaspora", "Je veux investir 10 000 euros au Sénégal : terrain, commerce ou immobilier locatif ? Compare les options et les risques"),
    ("diaspora", "Comment organiser le retour définitif de ma famille de 4 personnes à Dakar, avec scolarité et logement ?"),
    ("diaspora", "Quel est le meilleur moyen d'envoyer 500 euros par mois à ma famille : Wave, Orange Money ou Western Union ? Compare les frais"),
    ("commerçant", "Compare Wave, Orange Money et le paiement en espèces pour ma boutique de 30 clients par jour"),
    ("commerçant", "Optimise mes prix : j'achète à 2500 FCFA et je veux 30 % de marge, avec 200 FCFA de transport par article"),
    ("commerçant", "Quel plan d'action pour lancer ma boutique en ligne avec 300000 FCFA ? Priorités et étapes"),
    ("commerçant", "Quelles priorités pour ouvrir un restaurant à Saint-Louis avec 5 millions de FCFA ?"),
]

SIMPLES_HORS_ECHANTILLON = [
    ("touriste", "Pourquoi les Sénégalais disent-ils « inch'Allah » ?"),
    ("touriste", "Comment faire la bise au Sénégal ?"),
    ("touriste", "Où se trouve l'office du tourisme ? J'ai besoin d'un plan."),
    ("touriste", "Quel est le meilleur jus local à goûter ?"),
    ("touriste", "Pourquoi y a-t-il autant de monde au marché Kermel ?"),
    ("touriste", "Ce soir et demain, quel temps à Saly ?"),
    ("touriste", "Comment faire pour trouver un taxi à Dakar ?"),
    ("résident", "Qui organise la Biennale de Dakar ?"),
    ("résident", "Quelle est la priorité des piétons au passage clouté ?"),
    ("résident", "À quelle heure ferme la pharmacie ce soir ?"),
    ("diaspora", "Comment faire cuire du riz comme au Sénégal ?"),
    ("diaspora", "Pourquoi le baobab est-il si important ?"),
]

COMPLEXES_HORS_ECHANTILLON = [
    ("touriste", "Pourquoi choisir Saly plutôt que Somone pour 5 jours avec 3 enfants ?"),
    ("touriste", "Compare le coût de la vie à Dakar et à Thiès pour un couple"),
    ("touriste", "Organise-moi 4 jours à Saint-Louis pour 2 adultes et 2 enfants avec 400000 FCFA"),
    ("touriste", "Quel est le meilleur moyen de rejoindre Ziguinchor depuis Dakar : bus, bateau ou avion, avec un budget de 150000 FCFA ?"),
    ("diaspora", "Comment faire pour transférer 2000 euros par mois au Sénégal sans trop de frais ? Quelles options ?"),
    ("diaspora", "Comment faire pour scolariser mes 3 enfants à Dakar en revenant de France, quelles démarches et dans quel ordre ?"),
    ("diaspora", "Quels sont les avantages et inconvénients d'investir dans un terrain à Diamniadio ?"),
    ("commerçant", "Pourquoi mon commerce de 40 clients par jour ne dégage pas de marge avec 15 % de coûts ?"),
    ("commerçant", "Plan de financement pour ouvrir une boutique avec 1 million de FCFA : étapes et priorités"),
    ("commerçant", "Je dois choisir entre Wave et Orange Money pour mon commerce"),
]

SIMPLES = SIMPLES_MESURE + SIMPLES_HORS_ECHANTILLON
COMPLEXES = COMPLEXES_MESURE + COMPLEXES_HORS_ECHANTILLON


def parse(message, history=()):
    body = {"message": message, "history": [*history, {"role": "user", "content": message}], "language": "fr", "audience": "tourist"}
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload, body


def model_of(payload):
    return app_module._CHAT_SERVICE["model_kwargs"](payload, False)["model"]


@pytest.mark.parametrize("profile,question", SIMPLES)
def test_simple_question_stays_on_the_fast_model(profile, question):
    payload, _ = parse(question)
    assert payload["deep_reasoning"] is False, question
    assert payload["intent_context"]["needs_deep_reasoning"] is False
    assert model_of(payload) == FAST_MODEL


@pytest.mark.parametrize("profile,question", COMPLEXES)
def test_complex_request_keeps_the_deep_reasoning(profile, question):
    payload, _ = parse(question)
    assert payload["deep_reasoning"] is True, question
    assert model_of(payload) == COMPLEX_MODEL


def test_the_corpus_is_balanced_and_covers_every_profile():
    assert len(SIMPLES_MESURE) + len(COMPLEXES_MESURE) >= 40
    for questions in (SIMPLES, COMPLEXES):
        assert {profile for profile, _ in questions} == {"touriste", "résident", "diaspora", "commerçant"}
        assert len({question for _, question in questions}) == len(questions)


def test_known_limit_a_why_about_the_customers_of_my_business_stays_deep():
    """Limite connue, gardée par prudence : « pourquoi » + un projet d'activité (intention « project ») reste complexe.

    Une question de diagnostic de sa propre activité peut demander de raisonner ; on préfère un appel plus cher à une
    réponse trop courte. À revoir avec des questions réelles si le coût du modèle complexe devient un souci."""
    payload, _ = parse("Pourquoi mes clients paient-ils plus souvent avec Wave ?")
    assert payload["intent_context"]["intent"] == "project" and payload["deep_reasoning"] is True


def test_simple_first_questions_are_now_served_from_the_answer_cache():
    """Effet mesurable : une question sans raisonnement approfondi peut être mise en cache (et resservie)."""
    for question in ("Pourquoi le lac Rose est-il rose ?", "Comment faire pour dire bonjour en wolof ?"):
        payload, raw = parse(question)
        assert cache_key(payload, raw, model="m") is not None, question
    payload, raw = parse("Compare Saly et Somone pour une famille")
    assert cache_key(payload, raw, model="m") is None


# --- Règle, terme par terme ------------------------------------------------------------------------------------


def deep(query, intents=(), constraints=()):
    return should_use_deep_reasoning({"query": query, "intents": list(intents), "constraints": list(constraints)})


@pytest.mark.parametrize("query", [
    "Compare Saly et Somone", "Peux-tu comparer ces deux options", "Je veux un comparatif", "Quelle est la différence entre Wave et Orange Money",
    "Je dois choisir un hôtel", "Quel est le meilleur choix", "Quels avantages ?", "Quels inconvénients ?", "Optimise mon budget",
    "Wave versus Orange Money", "Wave vs Orange Money", "Quelles sont les étapes", "Quelle est la première étape",
])
def test_terms_that_announce_a_complex_request_are_enough_alone(query):
    assert deep(query) is True


@pytest.mark.parametrize("query", [
    "Pourquoi le ciel est bleu", "Comment faire un thé", "Où trouver un plan de Dakar", "Qui organise le Magal",
    "Quel est le meilleur moment pour visiter Gorée", "Quelle est la priorité à droite", "Comment organiser mon sac",
])
def test_ambiguous_terms_are_not_enough_alone(query):
    assert deep(query) is False


@pytest.mark.parametrize("query,intents,constraints", [
    ("Pourquoi mon budget ne suffit pas", (), ["budget=300000 fcfa"]),  # contrainte chiffrée
    ("Comment faire pour ouvrir un commerce", ["project"], ()),  # intention de décision
    ("Comment faire pour un passeport, dans quel ordre", (), ()),  # démarche à plusieurs temps
    ("Comment faire pour une carte, quelles démarches", (), ()),
    ("Quel est le meilleur moyen entre le bus et le taxi", (), ()),  # choix entre des options
    ("Quelles priorités pour mon restaurant", ["project"], ()),
])
def test_an_ambiguous_term_counts_with_a_second_sign_of_complexity(query, intents, constraints):
    assert deep(query, intents, constraints) is True


def test_moments_are_not_decision_constraints():
    assert deep("Où dîner", constraints=["ce soir", "demain"]) is False
    assert deep("Que faire", constraints=["demain"]) is False
    assert deep("Où dîner", intents=["project"], constraints=["demain"]) is False
    assert deep("Où dîner", constraints=["durée=3 jours", "budget=100000 fcfa"]) is True
    assert deep("Où dîner", constraints=["adultes=2", "enfants=2"]) is True
    assert deep("Où dîner", constraints=["famille", "ce soir"]) is False  # une seule contrainte chiffrée
    assert deep("Lancer mon commerce", intents=["project"], constraints=["budget=150000 fcfa"]) is True


def test_untouched_rules_still_work():
    assert deep("Bonjour", intents=["travel", "transport"]) is True  # deux intentions complexes dans un contexte construit à la main
    assert deep("Bonjour", intents=["travel"]) is False
    assert deep("Bonjour") is False
    assert should_use_deep_reasoning({}) is False
