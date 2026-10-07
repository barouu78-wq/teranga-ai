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
 ("fr","Combien vaut 100 euros en FCFA ?",["LIEUX PERTINENTS"]),
 ("fr","Parle-moi de Gorée",["REPÈRES PRATIQUES"]),
 ("fr","Raconte-moi l'histoire de Saint-Louis",["REPÈRES PRATIQUES"]),
 ("fr","Qu'est-ce que le thiéboudienne ?",["REPÈRES PRATIQUES"]),
 ("fr","Une question sur le Sénégal : qui était Senghor ?",["Police 17"]),
 ("fr","Créer un itinéraire de 5 jours",["NINEA"]),
 ("en","Tell me about Pink Lake",["REPÈRES PRATIQUES"]),
 ("fr","Quel temps fait-il à Dakar ?",["LIEUX PERTINENTS :\n- Parc national du Niokolo"]),
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


@pytest.mark.parametrize("lang,question,forbidden", NOISE, ids=[q for _, q, _ in NOISE])
def test_context_has_no_off_topic_block(lang, question, forbidden):
    context = _context(question, lang)
    assert not [text for text in forbidden if text in context]
