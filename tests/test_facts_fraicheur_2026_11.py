"""Vérification de fraîcheur du 1er novembre 2026 : repères corrigés après lecture des pages officielles.

Sources ouvertes le 01/11/2026 (détail en commentaire dans services/practical_facts.py) :
- fièvre jaune : communiqué du ministère sénégalais des Affaires étrangères relayé par lesoleil.sn (9 mars 2026)
  et isd.gov.gh (7 avril 2026), contre gov.uk (mise à jour du 19/10/2026) et travel.gc.ca (15/10/2026) ;
- passeport : gov.uk et travel.gc.ca ;
- carte d'identité : rapport de commission du projet de loi n° 21/2026 (vie-publique.sn) et lesoleil.sn
  (renvoi en commission, 29 septembre 2026).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import practical_context  # noqa: E402


def test_fievre_jaune_certificat_presente_comme_contradictoire_et_a_verifier():
    ctx = practical_context("Faut-il un vaccin pour aller au Sénégal ?")
    assert "Fièvre jaune : vaccin recommandé" in ctx
    # Plus d'affirmation ferme : les sources officielles se contredisent.
    assert "certificat exigé si l'on arrive" not in ctx
    assert "mars 2026" in ctx and "n'est pas obligatoire" in ctx
    assert "du Royaume-Uni et du Canada (octobre 2026)" in ctx
    assert "À vérifier auprès de l'ambassade du Sénégal et de la compagnie aérienne" in ctx


def test_passeport_six_mois_attribue_aux_sources():
    ctx = practical_context("Faut-il un visa pour aller au Sénégal avec un passeport français ?")
    assert "passeport valable au moins 6 mois" in ctx
    assert "Royaume-Uni" in ctx and "Canada" in ctx


def test_carte_identite_projet_de_prorogation_a_verifier():
    ctx = practical_context("Comment renouveler ma carte d'identité sénégalaise ?")
    assert "valable 10 ans (loi n° 2016-09" in ctx
    assert "projet de loi n° 21/2026" in ctx
    assert "renvoyé en commission le 29 septembre 2026" in ctx


def test_questions_voisines_sans_repere_fievre_jaune():
    # « vaccin » seul déclenche « sante », mais une question de recette ou de foot n'ajoute rien.
    assert "Fièvre jaune" not in practical_context("Recette du thiéboudienne au poisson")
    assert "21/2026" not in practical_context("Quel est le score du match Sénégal–Égypte ?")
