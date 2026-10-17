"""Repère « carte SIM » : Free Sénégal est devenu Yas (annonce de novembre 2024, sources en tête de
services/practical_facts.py). L'IA ne doit plus présenter « Free » comme le nom actuel de l'opérateur."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import practical_context  # noqa: E402


def test_le_repere_sim_nomme_yas_et_plus_free_seul():
    context = practical_context("quelle carte sim acheter a l aeroport ?")
    assert "Yas" in context
    assert "Orange, Free et Expresso" not in context
