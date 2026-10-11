"""Modes « guide » et « négociation » : ils ne se déclenchent que pour la bonne question.

Constat (batterie de questions réalistes, corps de requête identique à celui du site) : « quartier » et
« coin » faisaient répondre en guide touristique à un résident dont le quartier n'a plus d'eau, « souvenirs »
et « marché » lançaient la négociation pour une question de mémoire ou de marché du travail, et un
entraînement au marchandage restait actif après un changement de sujet.

Chaque cas négatif a son cas positif voisin : la bonne question déclenche toujours le bon mode.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.guide_modes import detect_modes  # noqa: E402

GUIDE_OUI = [
    "Salut je cherche une visite guidee de Goree",
    "Que voir a Saint-Louis ?",
    "Raconte-moi l'histoire de Gorée",
    "Quartier Médina à Dakar : c'est quoi l'histoire ?",
    "Sois mon guide dans le quartier de Ngor",
    "Je veux visiter la Médina de Dakar",
    "Balade à pied dans Saint-Louis",
    "Tell me about the history of Goree",
    "Be my guide: what to see in Dakar?",
]

GUIDE_NON = [
    # « quartier » et « coin » : vie quotidienne d'un résident
    "Mon quartier n'a pas d'eau depuis 3 jours, qui appeler ?",
    "Il y a beaucoup de vols dans mon quartier, que faire ?",
    "Mon quartier est inondé pendant l'hivernage, à qui s'adresser ?",
    "Je cherche un bon coin pour faire du jogging à Dakar",
    "Comment attirer les touristes dans mon quartier ?",
    "Quel quartier de Dakar est le plus calme pour dormir ?",
    # autres sens de « visite », « raconte », « patrimoine », « histoire de »
    "Je dois passer une visite médicale pour mon permis",
    "Je vais rendre visite à ma famille à Touba",
    "Raconte-moi une blague",
    "Je veux visiter un appartement à louer à Mermoz",
    "Il y a un patrimoine familial à partager entre mes frères",
    "L'histoire de ma carte d'identité perdue",
    "Histoire de mon visa refusé",
]

MARCHE_OUI = [
    "Comment négocier au marché Sandaga ?",
    "Je veux négocier le prix des tissus à Sandaga",
    "Combien payer un boubou au marché Sandaga ?",
    "Quels souvenirs rapporter du Sénégal ?",
    "Où acheter des souvenirs à Dakar ?",
    "Where to buy souvenirs in Dakar?",
    "How do I bargain at Sandaga market?",
    "Je veux marchander un masque",
    "C'est trop cher pour un masque, aide-moi à baisser le prix",
    "Comment négocier avec mon fournisseur ?",
    "Je suis prêt à négocier le prix de ces masques",  # « prêt » (accent retiré) n'est pas « un prêt »
    "On m'a volé mon sac au marché, comment négocier sans me faire avoir ?",  # le geste de négociation est demandé
]

MARCHE_NON = [
    # « souvenirs » : mémoire, pas achat
    "Mes souvenirs d'enfance à Dakar, comment les écrire dans un livre ?",
    "Les souvenirs de la colonisation à Gorée",
    # « marché » : économie, pas bazar
    "Comment est le marché du travail au Sénégal ?",
    "Le marché immobilier à Dakar est cher ?",
    "Le marché noir du dollar à Dakar",
    "Is the stock market a good way to invest in Senegal?",
    "Market opportunities in Senegal for my startup",
    # négociation qui n'est pas celle d'un marché
    "Je veux négocier mon loyer avec le propriétaire",
    "Comment négocier mon salaire ?",
    # vol ou perte : la question demande de l'aide, pas du marchandage
    "On m'a volé mon sac au marché Sandaga",
    "J'ai perdu mon téléphone au marché Kermel",
]


@pytest.mark.parametrize("question", GUIDE_OUI)
def test_la_visite_guidee_reste_en_mode_guide(question):
    assert "guide" in detect_modes(question), question


@pytest.mark.parametrize("question", GUIDE_NON)
def test_une_question_de_vie_quotidienne_n_active_pas_le_guide(question):
    assert "guide" not in detect_modes(question), question


@pytest.mark.parametrize("question", MARCHE_OUI)
def test_la_negociation_au_marche_reste_en_mode_marche(question):
    assert "market" in detect_modes(question), question


@pytest.mark.parametrize("question", MARCHE_NON)
def test_une_question_hors_marche_n_active_pas_la_negociation(question):
    assert "market" not in detect_modes(question), question


ENTRAINEMENT = [
    {"role": "user", "content": "Entraîne-moi à marchander un masque au marché"},
    {"role": "assistant", "content": "15 000 francs, mon ami !"},
]


@pytest.mark.parametrize("replique", [
    "Je te propose 5000",
    "Trop cher, 8000 dernier prix",
    "Pourquoi si cher ?",
    "D'accord, je prends deux masques",
    "Waaw, baax na",
])
def test_l_entrainement_continue_pour_une_replique_de_negociation(replique):
    history = ENTRAINEMENT + [{"role": "user", "content": replique}]
    assert detect_modes(replique, history) == {"market", "market_practice"}


@pytest.mark.parametrize("question", [
    "Quel temps fait-il demain ?",
    "Comment payer ma facture Senelec ?",
    "Où trouver une pharmacie de garde à Thiès ?",
    "What is the weather in Dakar?",
    "Comment apprendre le wolof ?",
    "Comment dit-on bonjour en français ?",
])
def test_l_entrainement_s_arrete_quand_le_sujet_change(question):
    history = ENTRAINEMENT + [{"role": "user", "content": question}]
    assert detect_modes(question, history) == set()


def test_stop_arrete_toujours_l_entrainement():
    history = ENTRAINEMENT + [{"role": "user", "content": "Stop, fais le bilan"}]
    assert detect_modes("Stop, fais le bilan", history) == set()


def _payload(question, audience="resident", history=None):
    """Corps identique à celui du site : la question courante est le dernier élément de history."""
    import app as app_module

    body = {
        "message": question, "language": "fr", "audience": audience,
        "history": (history or []) + [{"role": "user", "content": question}],
    }
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def test_le_contexte_d_un_resident_n_a_pas_la_consigne_de_guide():
    payload = _payload("Mon quartier n'a pas d'eau depuis 3 jours, qui appeler ?")
    assert "MODE GUIDE LOCAL" not in payload["instructions"]
    assert "modes" not in payload


def test_le_contexte_d_un_commercant_n_a_pas_la_consigne_de_negociation():
    payload = _payload("Comment est le marché du travail au Sénégal ?", audience="merchant")
    assert "MODE NÉGOCIATION" not in payload["instructions"]
    assert "modes" not in payload


def test_le_contexte_d_un_touriste_garde_ses_modes():
    guide = _payload("Salut je cherche une visite guidée de Gorée", audience="tourist")
    assert guide["modes"] == ["guide"] and "MODE GUIDE LOCAL" in guide["instructions"]
    marche = _payload("Je veux négocier le prix des tissus à Sandaga", audience="merchant")
    assert marche["modes"] == ["market"] and "MODE NÉGOCIATION AU MARCHÉ" in marche["instructions"]
    souvenirs = _payload("Quels souvenirs rapporter du Sénégal ?", audience="tourist")
    assert "MODE NÉGOCIATION AU MARCHÉ" in souvenirs["instructions"]
