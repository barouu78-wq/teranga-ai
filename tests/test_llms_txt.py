"""Contrats de découverte SEO/IA du site public."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_llms_txt_exposes_official_site_and_priority_topics():
    from app import app

    page = app.test_client().get("/llms.txt", base_url="https://teranga-ai.fr")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "https://teranga-ai.fr/" in body
    for path in (
        "/assistant-senegal",
        "/ia-senegal",
        "/dakar",
        "/voyage-senegal",
        "/transport-senegal",
        "/diaspora-senegalaise",
        "/emploi-senegal",
        "/formation-senegal",
        "/entreprendre-senegal",
        "/regions-senegal",
    ):
        assert f"https://teranga-ai.fr{path}" in body
    assert "Français, anglais et wolof" in body


def test_llms_txt_uses_real_line_breaks():
    from app import app

    body = app.test_client().get("/llms.txt").get_data(as_text=True)
    assert "\\n" not in body
    assert body.splitlines()[0] == "# Teranga AI" and "## Pages prioritaires" in body.splitlines()
