import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.guide_modes import detect_modes, mode_instructions


def test_market_and_guide_modes_are_detected_without_false_positives():
    assert detect_modes("Comment négocier au marché Sandaga ?") == {"market"}
    assert detect_modes("Raconte-moi l'histoire de Gorée") == {"guide"}
    assert detect_modes("I want to haggle at the market") == {"market"}
    assert detect_modes("Ça marche, merci") == set()
    assert detect_modes("Combien coûte un taxi ?") == set()


def test_practice_continues_until_stop():
    history = [{"role": "user", "content": "Entraîne-moi à marchander un masque au marché"}, {"role": "assistant", "content": "15 000 francs !"}]
    assert detect_modes("Je te propose 5000", history) == {"market", "market_practice"}
    assert detect_modes("Stop, fais le bilan", history) == set()


def test_a_huge_history_item_is_cut_before_analysis(monkeypatch):
    """Audit du 27 novembre 2026 : l'historique brut du navigateur était analysé en entier ; une seule réplique de
    3 Mo occupait le serveur ~40 s. Chaque réplique est coupée à 1 400 caractères (comme l'historique que l'IA
    reçoit) avant l'analyse."""
    from services import guide_modes

    vus = []
    normalize = guide_modes._normalize
    monkeypatch.setattr(guide_modes, "_normalize", lambda text: vus.append(len(str(text))) or normalize(text))
    enorme = "Entraîne-moi à marchander un masque au marché " + "z " * 1_600_000
    history = [{"role": "user", "content": enorme}, {"role": "assistant", "content": "15 000 francs !"}]
    # Le début de la réplique (l'entraînement au marché) compte toujours.
    assert detect_modes("Je te propose 5000", history) == {"market", "market_practice"}
    assert vus and max(vus) <= 1400, max(vus)


def test_a_request_seen_only_beyond_what_the_ai_sees_does_not_start_practice():
    """Relecture /code-review : une demande d'entraînement placée après le 1 400e caractère, que l'IA ne voit pas,
    ne doit pas activer le jeu de rôle."""
    loin = "x " * 750 + "Entraîne-moi à marchander un masque au marché"
    assert detect_modes("Je te propose 5000", [{"role": "user", "content": loin}]) == set()


def test_a_history_that_is_not_a_list_or_has_odd_content_is_ignored():
    assert detect_modes("Je te propose 5000", "pas une liste") == set()
    assert detect_modes("Je te propose 5000", [{"role": "user", "content": {"a": 1}}]) == set()
    assert detect_modes("Je te propose 5000", [{"role": "user", "content": None}]) == set()


def test_leading_spaces_do_not_hide_a_practice_request_the_ai_sees():
    """Relecture Codex de la PR #684 : le texte est nettoyé (comme pour l'IA) avant d'être coupé ; des espaces en tête
    ne doivent pas faire sortir du jeu de rôle."""
    import app as app_module

    history = [{"role": "user", "content": " " * 3000 + "Entraîne-moi à marchander un masque au marché"},
               {"role": "assistant", "content": "15 000 francs !"}]
    with app_module.app.test_request_context("/chat", method="POST",
                                             json={"message": "Je te propose 5000", "language": "fr", "history": history}):
        payload, error = app_module.parse_chat_payload()
    assert error is None and payload["modes"] == ["market", "market_practice"]


def test_the_chat_passes_a_bounded_history_to_mode_detection(monkeypatch):
    import app as app_module

    recu = {}
    monkeypatch.setattr(app_module, "detect_modes", lambda message, history=None: recu.update(h=history) or set())
    historique = [{"role": "user", "content": "z" * 50_000}] * 40
    with app_module.app.test_request_context("/chat", method="POST",
                                             json={"message": "Bonjour", "language": "fr", "history": historique}):
        app_module.parse_chat_payload()
    assert len(recu["h"]) <= app_module.MAX_HISTORY_ITEMS
    assert max(len(item["content"]) for item in recu["h"]) <= app_module.MAX_HISTORY_ITEM_LENGTH


def test_market_instructions_carry_wolof_phrases_and_no_invented_prices():
    import json
    from pathlib import Path

    knowledge = json.loads((Path(__file__).resolve().parents[1] / "data" / "senegal_knowledge.json").read_text(encoding="utf-8"))
    text = mode_instructions({"market", "market_practice"}, knowledge)
    assert "« Ñaata la ? » = C'est combien ?" in text
    assert "N'invente jamais de prix précis" in text and "joue le vendeur" in text
    assert "Sandaga" in text and "Soumbédioune" in text


def test_chat_payload_gets_guide_mode_and_place_history():
    import app as app_module

    with app_module.app.test_request_context("/chat", method="POST", json={"message": "Raconte-moi l'histoire de Gorée", "language": "fr"}):
        payload, error = app_module.parse_chat_payload()
    assert error is None and payload["modes"] == ["guide"]
    assert "MODE GUIDE LOCAL" in payload["instructions"]
    assert "Boubacar Joseph Ndiaye" in payload["instructions"]  # histoire détaillée transmise
