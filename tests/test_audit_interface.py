"""Audit de l'interface (règles de Vercel, 13 octobre 2026) : ce qui se vérifie sans navigateur.

Les tests dans un vrai navigateur sont dans tests/e2e/test_audit_interface.py.
"""
from pathlib import Path

from services.site_layout import site_header

HOME = (Path(__file__).resolve().parent.parent / "templates" / "home.html").read_text(encoding="utf-8")


def test_the_brand_name_is_never_machine_translated():
    """« Teranga AI » est un nom : la traduction automatique de Chrome ne doit pas le transformer."""
    entete = HOME.split('<div class="brand">', 1)[1].split("</div>", 2)[1]
    assert '<strong translate="no">Teranga <em>AI</em></strong>' in entete
    assert '<strong translate="no">Teranga <em>AI</em></strong>' in site_header()


def test_secondary_pages_start_with_a_skip_link_in_their_language():
    for lang, texte in (("fr", "Aller au contenu"), ("en", "Skip to content")):
        html = site_header(lang=lang)
        assert html.startswith(f'<a class="skip-link" href="#contenu">{texte}</a>'), lang
        assert html.endswith('<span id="contenu" tabindex="-1"></span>')


def test_home_has_a_single_main_region():
    assert HOME.count("<main") == 1 and HOME.count("</main>") == 1
    assert '<main id="stage" tabindex="-1">' in HOME
