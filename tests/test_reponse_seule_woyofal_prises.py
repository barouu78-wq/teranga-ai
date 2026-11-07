"""V5, étape 1 (suite) : Teranga répond seul aux questions fréquentes sur Woyofal et sur les prises électriques, sans
appeler le modèle : instantané, exact et gratuit (Go V5 du propriétaire, 6 et 7 novembre 2026).

La réponse est le repère vérifié de services/practical_facts.py, tel quel (sujets « factures » et « electricite ») :
le même texte que celui que l'IA reçoit, avec ses sources dans ce fichier (communiqué Senelec du 15/10/2024 relayé
par la presse, grille CRSE du 01/01/2026). Seule une question courte qui ne demande que ça est servie ainsi : une
situation (« mon compteur affiche une erreur »), une suite de conversation ou une autre langue que le français ou
l'anglais vont au modèle.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services import practical_facts
from services.quick_answers import quick_answer


def _faits(nom):
    return next(facts for name, _, facts in practical_facts.TOPICS if name == nom)


def _reponse(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize("message", [
    "Woyofal pourquoi trois codes ?",
    "Comment acheter du crédit Woyofal ?",
    "C'est quoi Woyofal ?",
    "Où acheter du Woyofal ?",
    "Woyofal",
    "Comment recharger mon compteur Woyofal ?",
])
def test_woyofal_recoit_le_repere_verifie(message):
    answer = _reponse(message)
    assert answer is not None, message
    for fait in _faits("factures"):
        assert fait in answer["reply"]
    assert "trois codes de 20 chiffres" in answer["reply"]
    assert answer["reply"].endswith("teranga-ai.fr/demarches-senegal")
    assert answer["theme"] == "electricite"


@pytest.mark.parametrize("message", [
    "Quelles prises électriques au Sénégal ?",
    "Quel voltage au Sénégal ?",
    "Faut-il un adaptateur pour le Sénégal ?",
    "Type de prise au Sénégal ?",
    "Quelle tension électrique à Dakar ?",
])
def test_les_prises_electriques_recoivent_le_repere_verifie(message):
    answer = _reponse(message)
    assert answer is not None, message
    assert answer["reply"] == _faits("electricite")[0]
    assert "230 V, 50 Hz" in answer["reply"]
    assert answer["theme"] == "electricite"


@pytest.mark.parametrize("message", [
    # Une situation, une erreur ou un détail : le modèle répond (avec le même repère dans son contexte).
    "Mon compteur Woyofal affiche erreur 05, que faire ?",
    "Woyofal ne marche plus depuis hier soir chez ma mère à Thiès",
    "J'ai payé Woyofal sur Wave mais je n'ai pas reçu le code",
    "Combien de kWh pour 5000 FCFA de Woyofal ?",
    "Prise de sang à Dakar ?",
    "Prise en charge par la CMU ?",
    "Faut-il un visa pour le Sénégal ?",
    "Mon chargeur de téléphone marche avec les prises du Sénégal ?",
])
def test_une_situation_ou_un_autre_sujet_va_au_modele(message):
    assert _reponse(message) is None, message


def test_une_suite_de_conversation_va_au_modele():
    raw = {"history": [{"role": "user", "content": "Je pars à Dakar"}, {"role": "assistant", "content": "Super !"},
                       {"role": "user", "content": "Quel voltage au Sénégal ?"}]}
    assert _reponse("Quel voltage au Sénégal ?", raw=raw) is None


def test_en_anglais_le_modele_repond():
    # Le repère est en français : pas de réponse prête dans une autre langue.
    assert _reponse("What plugs are used in Senegal?", language="en") is None
    assert _reponse("Woyofal", language="wo") is None
