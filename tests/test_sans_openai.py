"""Teranga sans OpenAI : de vraies conversations de plusieurs messages, l'IA en panne et sans secours Claude.

Choix du propriétaire (25 octobre 2026) : Teranga doit dépendre moins d'OpenAI. Ici, OpenAI échoue à chaque
appel et la clé Anthropic est absente : seules les réponses prêtes et la base vérifiée du site répondent. Une suite
de conversation (« Comment y aller ? » après Gorée) doit garder le sujet du fil au lieu de répondre « je n'ai pas
de réponse prête ». Aucun appel réseau.
"""

import json
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402

B = "https://teranga-ai.fr"
SANS_REPONSE = "je n'ai pas de réponse prête"
COMPTEUR = [0]


@pytest.fixture
def conversation(monkeypatch):
    """OpenAI en panne, pas de clé Anthropic : renvoie une fonction qui pose les questions dans le même fil."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def panne(**kwargs):
        raise RuntimeError("OpenAI indisponible (panne simulée)")

    monkeypatch.setattr(app_module.client.responses, "create", panne)
    COMPTEUR[0] += 1
    adresse = f"198.51.100.{20 + COMPTEUR[0]}"
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    historique = []

    def poser(question):
        historique.append({"role": "user", "content": question})
        reponse = client.post(
            "/chat",
            json={"message": question, "language": "fr", "history": historique},
            headers={"X-CSRF-Token": token, "Origin": B},
            base_url=B,
            environ_base={"REMOTE_ADDR": adresse},
        )
        evenements = [json.loads(ligne) for ligne in reponse.get_data(as_text=True).splitlines() if ligne.strip()]
        assert not any("error" in e for e in evenements), evenements
        texte = "".join(e.get("d", "") for e in evenements)
        historique.append({"role": "assistant", "content": texte})
        return texte

    return poser


def test_un_lieu_puis_comment_y_aller_puis_un_autre_lieu(conversation):
    assert "Île de Gorée" in conversation("Parle-moi de l'île de Gorée")
    suite = conversation("Comment y aller ?")
    assert SANS_REPONSE not in suite
    assert "Chaloupe depuis la gare maritime" in suite  # l'accès à Gorée, repris de la base
    autre = conversation("Et l'île de Saint-Louis ?")
    assert "Île de Saint-Louis" in autre and "Île de Gorée" not in autre


def test_un_plat_puis_un_autre(conversation):
    assert "Yassa" in conversation("C'est quoi le yassa ?")
    assert "Mafé" in conversation("Et le mafé ?")


def test_les_urgences_puis_une_precision(conversation):
    assert "17" in conversation("Quels sont les numéros d'urgence au Sénégal ?")
    suite = conversation("Et pour un incendie ?")
    assert SANS_REPONSE not in suite and "18" in suite


def test_le_visa_puis_une_precision(conversation):
    premiere = conversation("Faut-il un visa pour aller au Sénégal ?")
    assert "visa" in premiere.lower() and SANS_REPONSE not in premiere
    suite = conversation("Et pour combien de temps ?")
    assert SANS_REPONSE not in suite and "visa" in suite.lower()


def test_une_question_inconnue_reste_honnete(conversation):
    texte = conversation("Quel est le meilleur logiciel de comptabilité pour mon garage ?")
    assert SANS_REPONSE in texte  # jamais d'invention
