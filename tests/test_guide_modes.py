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
