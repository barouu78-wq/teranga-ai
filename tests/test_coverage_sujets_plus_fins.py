"""Journal des lacunes (/stats-ia) : une ligne « Autre » qui dit quelque chose.

Premier relevé (24 octobre 2026) : 6 questions sur 7 de la ligne « Autre » sans appui. Un banc de questions réalistes
passées dans le vrai contexte du chat montre d'où elles viennent :
  - les suivis (« Et pour y aller ? ») : le message seul n'a pas de sujet, alors que l'IA a reçu les fiches du fil ;
  - le Sénégal en bref (capitale, superficie, hymne…) : aucun thème, même quand la ligne « Profil » de la base était là ;
  - les questions sur Teranga AI elle-même (« Que peux-tu faire ? ») ;
  - des préambules qui ne sont pas des questions (« J'ai une question », « Je m'appelle Moussa »).
Rien de plus n'est conservé : toujours des compteurs par jour et par thème, jamais le texte.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.coverage_log import THEMES, chat_signals, classify, is_small_talk, subject_of, themes_of  # noqa: E402

PLACES = app_module.SENEGAL_KNOWLEDGE["places"]


def _real_payload(message, history=None):
    body = {"message": message, "language": "fr"}
    if history:
        body["history"] = history
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def _states(message, history=None):
    payload = _real_payload(message, history)
    return classify(subject_of(payload, PLACES), chat_signals(payload, PLACES))


# --- Suivis ---------------------------------------------------------------------------------------------------------

def test_un_suivi_sans_sujet_prend_le_sujet_du_fil():
    fil = [{"role": "user", "content": "Parle-moi de Gorée"}, {"role": "assistant", "content": "Gorée est…"}]
    assert _states("Et pour y aller ?", fil) == {"voyage": True}
    fil = [{"role": "user", "content": "Parle-moi du lac Rose"}, {"role": "assistant", "content": "Le lac Rose est…"}]
    assert _states("Et pour y aller ?", fil) == {"nature": True}


def test_un_suivi_avec_son_propre_sujet_garde_le_sien():
    fil = [{"role": "user", "content": "Parle-moi du lac Rose"}, {"role": "assistant", "content": "Le lac Rose est…"}]
    assert set(_states("Faut-il un visa ?", fil)) == {"visa"}


def test_sans_fil_une_question_sans_sujet_reste_dans_autre():
    assert _states("zxqv blorp") == {"autre": False}


def test_sans_fil_le_sujet_est_la_question():
    assert subject_of({"message": "Comment divorcer ?", "contextual_query": "comment divorcer ?"}) == "Comment divorcer ?"
    assert subject_of({"message": "Comment divorcer ?"}) == "Comment divorcer ?"


# --- Le Sénégal en bref ---------------------------------------------------------------------------------------------

def test_le_theme_pays_existe():
    assert "pays" in {theme.id for theme in THEMES}


@pytest.mark.parametrize("question", [
    "Quelle est la superficie du Sénégal ?",
    "Combien de régions au Sénégal ?",
    "Quelle est la capitale du Sénégal ?",
])
def test_le_profil_du_pays_dans_le_contexte_couvre_la_question(question):
    assert _states(question) == {"pays": True}


@pytest.mark.parametrize("question", [
    "Quel est l'hymne national du Sénégal ?",
    "Quel est le drapeau du Sénégal ?",
    "Combien d'habitants au Sénégal ?",
])
def test_ce_que_la_base_ne_dit_pas_reste_non_couvert(question):
    assert _states(question) == {"pays": False}


def test_la_ligne_des_reperes_nationaux_ne_couvre_que_la_capitale():
    # Toujours présente dans le contexte : elle ne couvre pas une question qu'elle ne traite pas.
    signals = chat_signals(_real_payload("Quel est l'hymne national du Sénégal ?"), PLACES)
    assert "capitale" not in signals and "profil" not in signals
    assert "capitale" in chat_signals(_real_payload("Quelle est la capitale du Sénégal ?"), PLACES)


# --- Questions sur Teranga AI ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Qui es-tu ?",
    "Que peux-tu faire ?",
    "Qu'est-ce que tu sais faire ?",
    "C'est quoi Teranga AI ?",
    "Qui a créé Teranga AI ?",
])
def test_les_questions_sur_teranga_ai_ont_leur_ligne(question):
    assert themes_of(question) == ["teranga_ai"]


def test_la_teranga_reste_de_la_culture():
    assert "culture" in themes_of("C'est quoi la teranga sénégalaise ?")
    assert "culture" not in themes_of("C'est quoi Teranga AI ?")


def test_rien_dans_le_contexte_ne_decrit_teranga_ai():
    assert _states("Que peux-tu faire ?") == {"teranga_ai": False}


# --- Voyage ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Que faire au Sénégal en une semaine ?",
    "Je pars au Sénégal en décembre, des conseils ?",
    "Que mettre dans sa valise pour le Sénégal ?",
])
def test_les_questions_de_voyage_sans_lieu_sont_reconnues(question):
    assert "voyage" in themes_of(question)


@pytest.mark.parametrize("question", [
    "Je vis en France, je veux m'installer au Sénégal",
    "Aides pour le retour des Sénégalais de l'extérieur",
])
def test_les_tournures_de_la_diaspora_sont_reconnues(question):
    assert "diaspora" in themes_of(question)


# --- Préambules -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    "Bonjour, je m'appelle Moussa",
    "Je m'appelle Awa",
    "J'ai une question",
    "Bonjour, j'ai une petite question",
    "Peux-tu m'aider ?",
    "Est-ce que tu peux m'aider ?",
    "Aide-moi",
])
def test_un_preambule_n_est_pas_une_question(message):
    assert is_small_talk(message)


@pytest.mark.parametrize("message", [
    "Je m'appelle Moussa et je cherche un hôtel à Saly",
    "Peux-tu m'aider à trouver un hôtel ?",
    "J'ai une question sur le visa",
])
def test_un_preambule_suivi_d_une_vraie_question_est_compte(message):
    assert not is_small_talk(message)
