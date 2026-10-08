"""Banc d'essai « pratique » : le contexte donné à l'IA contient le bon fait, mot pour mot.

Les vérifications portent sur des phrases exactes (« Police 17 », « 655,957 ») : un
simple « 17 » pouvait venir d'une date et faire croire que l'information était là.
Les cas « bruit » vérifient qu'aucun bloc hors sujet n'est ajouté.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402

PROBES = [
 # urgences et santé
 ("fr","Quels sont les numéros d'urgence au Sénégal ?",["Police 17","Sapeurs-pompiers 18","1515"]),
 ("fr","J'ai eu un accident, qui appeler ?",["Sapeurs-pompiers 18","SAMU"]),
 ("en","What is the police number in Senegal?",["Police 17"]),
 ("fr","Mon enfant a de la fièvre à Dakar, que faire ?",["SAMU"]),
 ("fr","Faut-il un vaccin pour aller au Sénégal ?",["Fièvre jaune : vaccin recommandé"]),
 # fêtes
 ("fr","C'est quand la Tabaski ?",["Tabaski (Aïd el-Kébir)","2027"]),
 ("fr","Quand est le Magal de Touba ?",["Grand Magal de Touba (Touba) :"]),
 ("fr","Date de la Korité 2027",["Korité (Aïd el-Fitr) (Tout le pays) :"]),
 ("en","When is the Saint-Louis jazz festival?",["Festival international de jazz de Saint-Louis","mai 2027"]),
 ("fr","Quels jours fériés en décembre ?",["Noël"]),
 # argent
 ("fr","Combien vaut 100 euros en FCFA ?",["655,957"]),
 ("en","How much is 50 euros in CFA francs?",["655,957"]),
 ("fr","Comment payer au Sénégal ? Wave ?",["Wave"]),
 # argent : arnaques et mobile money
 ("fr","On m'a appelé pour me demander un code reçu par SMS, c'est une arnaque ?",["ne jamais donner son code secret ni un code reçu par SMS"]),
 ("fr","J'ai reçu un SMS pour une amende avec un lien de paiement",["n'envoient pas de SMS avec un lien cliquable"]),
 ("fr","Comment reconnaître un faux billet de 10 000 FCFA ?",["rubrique « Billets et pièces »"]),
 ("fr","Un intermédiaire me promet un visa contre de l'argent, c'est sûr ?",["« facilitateurs »"]),
 ("fr","Un faux policier m'a demandé de l'argent à Dakar",["la carte professionnelle"]),
 ("fr","Comment louer un appartement à Dakar à distance sans arnaque ?",["ne rien payer, même un « acompte de réservation »"]),
 ("fr","Mon frère m'écrit d'un nouveau numéro et demande de l'argent en urgence",["rappeler le proche sur son ancien numéro"]),
 ("fr","Mon compte WhatsApp a été piraté",["Faux proche, numéro usurpé, carte SIM"]),
 ("fr","Quelles arnaques à éviter à Dakar pour un touriste ?",["vols à la tire"]),
 ("en","Common scams for tourists in Senegal",["ne jamais envoyer d'argent à quelqu'un rencontré en ligne"]),
 ("fr","Comment se protéger de la fraude au mobile money ?",["raccrocher et rappeler","Code secret : il est personnel"]),
 ("fr","Comment fonctionne Wave ? À quoi ça sert ?",["recharger du crédit ou un forfait"]),
 ("fr","C'est quoi Free Money ?",["Free Sénégal est devenu Yas"]),
 ("fr","Comment protéger mon code secret Orange Money ?",["Code secret : il est personnel"]),
 ("fr","J'ai envoyé de l'argent au mauvais numéro avec Orange Money",["la référence de la transaction"]),
 ("fr","Quelqu'un dit m'avoir envoyé de l'argent par erreur et me demande de le renvoyer",["ne rien renvoyer ni donner de code"]),
 ("fr","Que faire si on m'a volé mon argent sur Wave ?",["Division spéciale de cybersécurité"]),
 ("fr","Où se plaindre si Wave ne me rembourse pas ?",["service de plaintes et réclamations"]),
 ("en","Someone called pretending to be from Wave and asked for my PIN code",["Code secret : il est personnel"]),
 # transport
 ("fr","Comment aller de l'aéroport AIBD à Dakar ?",["environ 45 km du centre de Dakar"]),
 ("fr","Comment aller en Casamance depuis Dakar ?",["bateau de nuit Dakar–Ziguinchor"]),
 ("fr","C'est quoi un sept-places ?",["sept-places depuis la gare routière"]),
 ("fr","Prendre le TER à Dakar",["TER Dakar ↔ Diamniadio"]),
 ("fr","Comment aller à Saint-Louis depuis Dakar ?",["Saint-Louis"]),
 # lieux
 ("fr","Que voir à Kédougou ?",["Kédougou"]),
 ("fr","Le désert de Lompoul",["Lompoul"]),
 ("fr","Visiter le Djoudj",["Djoudj"]),
 ("fr","Cap Skirring c'est bien ?",["Skirring"]),
 ("fr","Que faire à Saly ?",["Saly"]),
 ("fr","Le pays Bassari",["Bassari"]),
 ("fr","Visiter Touba",["Touba"]),
 ("fr","Que voir à Ziguinchor ?",["Ziguinchor"]),
 ("fr","Que faire à Thiès ?",["Thiès"]),
 ("fr","Que voir à Kaolack ?",["Kaolack"]),
 ("fr","Visiter Podor",["Podor"]),
 ("fr","Que faire à Tambacounda ?",["Tambacounda"]),
 ("en","What to see in Saint-Louis?",["Saint-Louis","Faidherbe"]),
 ("en","Is Gorée worth visiting?",["Gorée"]),
 # cuisine
 ("fr","C'est quoi le yassa ?",["Yassa"]),
 ("fr","Le mafé c'est quoi ?",["Mafé"]),
 ("fr","Qu'est-ce que le bissap ?",["Bissap"]),
 ("en","What is the national dish of Senegal?",["Thiéboudienne"]),
 # langue
 ("fr","Comment dire bonjour en wolof ?",["Salaam aleekum"]),
 ("fr","Comment dire merci en wolof ?",["Jërëjëf"]),
 ("en","How do I say thank you in Wolof?",["Jërëjëf"]),
 # culture / histoire
 ("fr","Qui était Cheikh Anta Diop ?",["Cheikh Anta Diop"]),
 ("fr","Qui est Senghor ?",["Senghor"]),
 ("fr","Histoire de l'indépendance du Sénégal",["1960"]),
 ("fr","Qui est Lat Dior ?",["Lat Dior"]),
 # pratique
 ("fr","Quelle est la meilleure période pour visiter le Sénégal ?",["Saison sèche environ de novembre à mai"]),
 ("fr","Quelle carte SIM acheter au Sénégal ?",["Orange, Free et Expresso"]),
 ("fr","Quel type de prise électrique au Sénégal ?",["230 V"]),
 ("fr","Combien coûte un taxi à Dakar ?",["fixer le prix avant de monter"]),
 ("fr","Comment négocier au marché ?",["NÉGOCIATION"]),
 ("fr","Quel est le décalage horaire avec Paris ?",["UTC+0"]),
 ("fr","Faut-il un visa pour un Français ?",["moins de 90 jours"]),
 ("fr","Quelle langue parle-t-on au Sénégal ?",["langue officielle","wolof est la langue la plus parlée"]),
 ("fr","Le Sénégal est-il un pays sûr ?",["Police 17","pickpockets"]),
 # diaspora / résident
 ("fr","Comment envoyer de l'argent au Sénégal ?",["Envoyer de l'argent vers le Sénégal"]),
 ("fr","Comment créer une entreprise au Sénégal ?",["guichet unique de l'APIX"]),
 ("fr","Où trouver une pharmacie de garde à Dakar ?",["Pharmacie de garde"]),
 # papiers, factures, protection sociale, études
 ("fr","Comment renouveler ma carte d'identité sénégalaise ?",["25 septembre 2026","copie littérale"]),
 ("fr","Je vis en France, comment renouveler mon passeport sénégalais ?",["à l'ambassade ou au consulat du Sénégal"]),
 ("fr","Comment obtenir un extrait de naissance ?",["centre d'état civil"]),
 ("fr","Comment faire un jugement supplétif ?",["jugement d'autorisation d'inscription"]),
 ("fr","Comment demander mon casier judiciaire ?",["greffe du tribunal"]),
 ("fr","C'est quoi e-Senegal ?",["e-Senegal (lancée en mars 2026)"]),
 ("fr","Comment recharger mon compteur Woyofal ?",["code de 20 chiffres"]),
 ("fr","Mon compteur Senelec demande trois codes",["trois codes de 20 chiffres"]),
 ("fr","C'est quoi la CMU au Sénégal ?",["Agence de la CMU"]),
 ("fr","Comment toucher la bourse de sécurité familiale ?",["Bourse de sécurité familiale (BSF)"]),
 ("fr","À quoi sert l'IPRES ?",["l'IPRES gère les retraites"]),
 ("fr","Comment s'inscrire à Campusen après le bac ?",["orientation.campusen.sn"]),
 ("en","How do I get my Senegalese ID card renewed?",["Carte d'identité biométrique CEDEAO"]),
]

HARD=[
 ("en","Do I need a visa to visit Senegal as an American?",["moins de 90 jours"]),
 ("en","Is it safe to travel to Senegal?",["Police 17"]),
 ("en","What plug type is used in Senegal?",["230 V"]),
 ("en","Best time to visit Senegal?",["Saison sèche"]),
 ("en","How do I get from Dakar airport to the city?",["45 km"]),
 ("en","When is Tabaski this year?",["Tabaski (Aïd el-Kébir)"]),
 ("en","Can I pay with my phone in Senegal?",["Wave et Orange Money"]),
 ("en","Where can I buy a SIM card in Dakar?",["Orange, Free et Expresso"]),
 ("en","What languages are spoken in Senegal?",["wolof est la langue la plus parlée"]),
 ("fr","Je me suis fait voler mon téléphone",["Police 17"]),
 ("fr","On parle quelle langue à Dakar ?",["wolof est la langue la plus parlée"]),
 ("fr","Il y a le paludisme au Sénégal ?",["Paludisme"]),
 ("fr","On peut boire l'eau du robinet ?",["eau en bouteille"]),
 ("fr","Quelle heure est-il à Dakar par rapport à Paris ?",["UTC+0"]),
 ("fr","Il pleut quand au Sénégal ?",["saison des pluies"]),
 ("fr","C'est quand la fin du ramadan ?",["Korité (Aïd el-Fitr) (Tout le pays) :"]),
 ("fr","La fête du mouton c'est quand ?",["Tabaski (Aïd el-Kébir)"]),
 ("fr","Je veux ouvrir une boutique, comment créer mon activité ?",["NINEA"]),
 ("fr","Combien de temps en bateau pour Ziguinchor ?",["environ 15 h"]),
 ("fr","Je veux louer une voiture à l'aéroport",["AIBD"]),
]

NOISE=[  # (question, textes qui NE doivent PAS apparaître)
 ("fr","Combien vaut 100 euros en FCFA ?",["LIEUX PERTINENTS","Faux SMS et faux liens","Code secret : il est personnel"]),
 # argent : questions voisines des arnaques et du mobile money qui ne doivent rien ajouter
 ("fr","Qui joue dans le film L'Arnaque avec Paul Newman ?",["REPÈRES PRATIQUES"]),
 ("fr","Que penser de la série Netflix sur une arnaque financière ?",["REPÈRES PRATIQUES"]),
 ("fr","Je suis volontaire pour une ONG au Sénégal",["REPÈRES PRATIQUES"]),
 ("fr","Comment fonctionne le tirage au sort de la CAN ?",["REPÈRES PRATIQUES"]),
 ("fr","Je cherche un billet d'avion pour Dakar",["REPÈRES PRATIQUES"]),
 ("fr","Y a-t-il de la fraude électorale au Sénégal ?",["REPÈRES PRATIQUES"]),
 ("fr","Quel est le code postal de Dakar ?",["REPÈRES PRATIQUES"]),
 ("fr","Peut-on louer un appartement à Dakar pour un mois ?",["REPÈRES PRATIQUES"]),
 ("fr","Raconte l'histoire du billet de 10 000 FCFA",["rubrique « Billets et pièces »","Faux SMS et faux liens"]),
 ("fr","Le surf à Ngor : la wave est-elle bonne en novembre ?",["Code secret : il est personnel"]),
 ("fr","Mon opérateur Orange a-t-il du réseau à Kédougou ?",["Code secret : il est personnel","Faux SMS et faux liens"]),
 ("fr","Parle-moi de Gorée",["REPÈRES PRATIQUES"]),
 ("fr","Raconte-moi l'histoire de Saint-Louis",["REPÈRES PRATIQUES"]),
 ("fr","Qu'est-ce que le thiéboudienne ?",["REPÈRES PRATIQUES"]),
 ("fr","Une question sur le Sénégal : qui était Senghor ?",["Police 17"]),
 ("fr","Créer un itinéraire de 5 jours",["NINEA"]),
 ("en","Tell me about Pink Lake",["REPÈRES PRATIQUES"]),
 ("fr","Quel temps fait-il à Dakar ?",["LIEUX PERTINENTS :\n- Parc national du Niokolo"]),
 ("fr","Le Sénégal est-il un pays agréable ?",["CEDEAO","Woyofal","Campusen"]),
 ("fr","Parle-moi de la Maison des Esclaves",["Woyofal","Campusen","CEDEAO"]),
 ("fr","Comment aller à l'université Cheikh Anta Diop ?",["Campusen"]),
]


def _context(question, lang):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


@pytest.mark.parametrize("lang,question,expected", PROBES + HARD, ids=[q for _, q, _ in PROBES + HARD])
def test_context_has_the_exact_fact(lang, question, expected):
    context = _context(question, lang).casefold()
    missing = [fact for fact in expected if fact.casefold() not in context]
    assert not missing, f"Faits absents du contexte : {missing}"


FOLLOW_UPS = [
    ("fr", "Et pour y aller ?", "Parle-moi du Lac Rose", "Lac Rose"),
    ("fr", "Combien de temps faut-il pour la visite ?", "Je veux visiter Gorée", "Gorée"),
    ("en", "And how do I get there?", "Tell me about Saint-Louis", "Saint-Louis"),
]

ROUND_2 = [
    ("wo", "Fan la police bi nekk ? Numéro urgence", ["Police 17"]),
    ("wo", "Ñaata la euro ci CFA ?", ["655,957"]),
    ("fr", "Je vis en France, comment acheter un terrain au Sénégal sans arnaque ?", ["titre foncier"]),
    ("fr", "Comment vendre sur WhatsApp ?", ["WhatsApp Business"]),
    ("fr", "Je rentre au pays pour la Tabaski, conseils ?", ["Tabaski (Aïd el-Kébir)"]),
]


@pytest.mark.parametrize("lang,question,expected", ROUND_2, ids=[q for _, q, _ in ROUND_2])
def test_context_round_two(lang, question, expected):
    context = _context(question, lang).casefold()
    assert not [fact for fact in expected if fact.casefold() not in context]


@pytest.mark.parametrize("lang,question,previous,place", FOLLOW_UPS, ids=[q for _, q, _, _ in FOLLOW_UPS])
def test_follow_up_keeps_the_place_of_the_previous_question(lang, question, previous, place):
    body = {"message": question, "language": lang, "history": [
        {"role": "user", "content": previous}, {"role": "assistant", "content": f"{place} : réponse précédente."}]}
    with app.test_request_context("/chat", method="POST", json=body):
        payload, error = parse_chat_payload()
    assert error is None and place.casefold() in payload["instructions"].replace(question, " ").casefold()


@pytest.mark.parametrize("lang,question,forbidden", NOISE, ids=[q for _, q, _ in NOISE])
def test_context_has_no_off_topic_block(lang, question, forbidden):
    context = _context(question, lang)
    assert not [text for text in forbidden if text in context]
