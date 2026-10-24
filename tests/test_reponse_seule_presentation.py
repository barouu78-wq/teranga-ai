"""« Qui es-tu ? », « Que peux-tu faire ? » : Teranga se présente seul, sans appeler le modèle.

Relevé /stats-ia du 24 octobre 2026 : rien dans le contexte de l'IA ne décrit le service, qui pouvait donc inventer
des fonctions. La réponse prête ne cite que des outils et des pages qui existent (chaque adresse est ouverte ici), et
présente Teranga comme l'assistant de toute la population : Sénégalais au pays, diaspora, commerçants, voyageurs.
"""

import datetime as dt
import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.quick_answers import quick_answer  # noqa: E402
from tests.test_coverage_log import FakeRedis, _chat  # noqa: E402


def _reponse(message, language="fr", history=None):
    raw = {"message": message, "language": language}
    if history:
        raw["history"] = history
    answer = quick_answer({"message": message, "language": language}, raw)
    return answer["reply"] if answer else None


@pytest.mark.parametrize("message", [
    "Qui es-tu ?",
    "Tu es qui ?",
    "Que peux-tu faire ?",
    "Qu'est-ce que tu sais faire ?",
    "Tu sers à quoi ?",
    "C'est quoi Teranga AI ?",
    "Présente-toi",
    "Comment peux-tu m'aider ?",
    "Bonjour, que peux-tu faire exactement ?",
])
def test_teranga_se_presente(message):
    reply = _reponse(message)
    assert reply is not None
    assert reply.startswith("Je suis Teranga AI, l'assistant du Sénégal, pour tout le monde")
    for public in ("Sénégalais au pays", "diaspora", "commerçants", "voyageurs"):
        assert public in reply
    assert "en français, en anglais ou en wolof" in reply
    assert "pulaar" not in reply.lower()  # pas réintroduit sans décision du propriétaire


def test_chaque_page_citee_existe():
    reply = _reponse("Que peux-tu faire ?")
    paths = re.findall(r"teranga-ai\.fr(/[a-z0-9/-]+)", reply)
    assert {"/urgences", "/calendrier-fetes-senegal", "/trip-planner", "/lieux"} <= set(paths)
    client = app_module.app.test_client()
    for path in paths:
        response = client.get(path, base_url="https://teranga-ai.fr")
        assert response.status_code == 200, path


def test_les_outils_cites_existent_sur_l_accueil():
    home = app_module.app.test_client().get("/", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert 'aria-label="Parler"' in home              # micro
    assert 'aria-label="Convertisseur de devises"' in home
    assert 'data-lang="wo"' in home                    # interface en wolof


@pytest.mark.parametrize("message", [
    "Que peux-tu faire pour mon visa ?",
    "Qui es-tu et quelle heure est-il à Dakar ?",
    "Que peux-tu faire contre la fièvre ?",
    "Comment ça marche le TER ?",
    "Qui est le président du Sénégal ?",
    "C'est quoi la teranga ?",  # l'hospitalité sénégalaise, pas le site
])
def test_une_vraie_question_va_au_modele(message):
    reply = _reponse(message)
    assert reply is None or not reply.startswith("Je suis Teranga AI")


def test_en_anglais_et_en_cours_de_conversation_le_modele_repond():
    assert _reponse("What can you do?", language="en") is None
    fil = [{"role": "user", "content": "Parle-moi de Gorée"}, {"role": "assistant", "content": "Gorée est…"}]
    assert _reponse("Que peux-tu faire ?", history=fil) is None


def test_une_reponse_prete_compte_comme_couverte_dans_stats_ia(monkeypatch):
    log = app_module.COVERAGE_LOG
    redis = FakeRedis()
    monkeypatch.setattr(log, "redis", redis)
    monkeypatch.setattr(log, "_background", False)
    monkeypatch.setattr(log, "_memory", {})
    response, _ = _chat("203.0.113.181", "Que peux-tu faire ?")
    assert response.status_code == 200
    assert response.get_json()["reply"].startswith("Je suis Teranga AI")
    counters = redis.hashes[f"teranga:coverage:{dt.date.today().isoformat()}"]
    assert counters.get("teranga_ai|c") == 1 and "teranga_ai|n" not in counters
