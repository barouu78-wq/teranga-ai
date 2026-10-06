"""Script de comparatif OpenAI / Claude : lecture du banc d'essai et rapport, sans appel réel."""

import os
import runpy
import sys
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "compare_ai.py")


def test_compare_script_writes_side_by_side_report(monkeypatch, tmp_path):
    module = runpy.run_path(SCRIPT, run_name="compare_ai")
    assert len(module["load_bench"]()) == 50
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "openai")  # le script change cette variable : restaurée après le test
    answer = SimpleNamespace(output_text="Prends la chaloupe à la gare maritime pour Gorée.", sources=[],
                             usage=SimpleNamespace(input_tokens=1000, output_tokens=200))
    monkeypatch.setattr(app_module, "create_response", lambda payload, stream: answer)
    module["main"].__globals__["claude_response"] = lambda prompt, **kw: answer
    out = tmp_path / "comparatif.md"
    monkeypatch.setattr(sys, "argv", ["compare_ai.py", "--limite", "1", "--prix-claude", "5,25", "--sortie", str(out)])
    module["main"]()
    report = out.read_text(encoding="utf-8")
    assert "Gorée" in report and "3 / 3" in report and "0.01 $" in report and "prix non fourni" in report
