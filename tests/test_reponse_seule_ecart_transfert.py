"""Teranga calcule seul ce qu'un transfert d'argent vers le Sénégal a coûté sur le change, sans appeler le modèle.

Envoyer de l'argent est la question n°1 de la diaspora (docs/PLAN-DIASPORA.md). Quand la question donne la somme
envoyée en euros et la somme reçue en FCFA, l'écart avec la parité fixe (1 € = 655,957 FCFA, repère vérifié) est un
coût du change : il se calcule (services/calculators.py), aucun fait nouveau n'est ajouté. Valeurs attendues
calculées à la main : 200 × 655,957 = 131 191,4 FCFA ; 131 191,4 − 128 000 = 3 191,4 FCFA ;
200 − 128 000 / 655,957 = 4,8653 € ; 4,8653 / 200 = 2,43 %.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services.quick_answers import quick_answer


def _reponse(message, language="fr", **raw):
    answer = quick_answer({"message": message, "language": language}, raw)
    return answer["reply"] if answer else None


def test_l_ecart_d_un_transfert_est_calcule_en_fcfa_en_euros_et_en_pourcentage():
    reply = _reponse("J'ai envoyé 200 € et ma famille a reçu 128 000 FCFA, combien j'ai perdu ?")
    assert reply is not None
    assert "Au taux officiel (parité fixe 1 € = 655,957 FCFA), 200 € = 131 191 FCFA." in reply
    assert "Montant reçu : 128 000 FCFA, soit 3 191 FCFA de moins (4,87 €, 2,43 % de la somme envoyée)." in reply
    assert "en plus des frais payés à l'envoi" in reply


@pytest.mark.parametrize("message", [
    "envoyé 150 euros, reçu 95.000 fcfa",
    "Ma famille a reçu 95 000 FCFA pour 150 € envoyés",
    "j'ai transféré 150 € ils ont touché 95 000 F CFA",
])
def test_les_formulations_courantes_sont_comprises(message):
    reply = _reponse(message)
    assert reply is not None
    # 150 × 655,957 = 98 393,55 ; 98 393,55 − 95 000 = 3 393,55 → 3 394 FCFA.
    assert "150 € = 98 394 FCFA" in reply
    assert "3 394 FCFA de moins" in reply


def test_un_montant_au_dessus_de_la_parite_est_dit_tel_quel():
    # Relecture Codex de #516 : 66 000 FCFA pour 100 € n'est pas « conforme à la parité » (65 595,70 FCFA),
    # c'est 404 FCFA de plus (66 000 − 65 595,70 = 404,30).
    reply = _reponse("J'ai envoyé 100 € et reçu 66 000 FCFA")
    assert reply is not None
    assert "Montant reçu : 66 000 FCFA, soit 404 FCFA de plus que la valeur à la parité" in reply
    assert "correspond à la parité" not in reply
    assert "de moins" not in reply


def test_un_montant_conforme_a_la_parite_n_a_pas_de_cout_de_change():
    reply = _reponse("J'ai envoyé 100 € et reçu 65 596 FCFA")
    assert reply is not None
    assert "correspond à la parité" in reply
    assert "de moins" not in reply


@pytest.mark.parametrize("message", [
    "J'ai envoyé 200 €",  # pas de montant reçu
    "J'ai envoyé 100 000 FCFA et reçu 150 €",  # dans l'autre sens : le modèle répond
    "J'ai envoyé 200 € avec 5 € de frais, reçu 128 000 FCFA",  # trois montants
    "200 € envoyés, 128 000 FCFA, c'est normal ?",  # rien ne dit ce qui a été reçu
    "100 euros en FCFA ?",  # simple conversion : autre réponse prête
])
def test_les_autres_questions_ne_recoivent_pas_ce_calcul(message):
    reply = _reponse(message)
    # « Montant reçu » est dans les deux réponses de transfert (écart ou parité respectée) : aucune ne doit partir.
    assert reply is None or "Montant reçu" not in reply


def test_en_anglais_ou_avec_un_historique_le_modele_repond():
    assert _reponse("I sent 200 € and they received 128 000 FCFA", language="en") is None
    history = [{"role": "user", "content": "Bonjour"}, {"role": "assistant", "content": "Bonjour !"}]
    assert _reponse("J'ai envoyé 200 € et reçu 128 000 FCFA", history=history) is None
