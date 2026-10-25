"""Accueil : les glyphes décoratifs des boutons sont muets pour les lecteurs d'écran, la marque n'est pas traduite.

Audit V3 (règles d'interface de Vercel, 25 octobre 2026) :
- les symboles des boutons de profil (✦ ✈ ⌂ ↔ ◆) et des parcours (🌍 🇸🇳 ✦) étaient lus à voix haute (« avion »,
  « globe terrestre », « drapeau : Sénégal ») avant le vrai libellé du bouton : ils portent aria-hidden="true" ;
- « Teranga AI » dans le texte de la page pouvait être traduit par Chrome : il porte translate="no", comme l'en-tête.
Changement invisible à l'écran.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

HOME = (Path(__file__).resolve().parents[1] / "templates" / "home.html").read_text(encoding="utf-8")


class _Glyphs(HTMLParser):
    """Relève les <span> enfants directs des boutons de profil et de parcours."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.in_strip = 0
        self.glyphs = []  # (texte, attributs)
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("id") == "journeyStrip":
            self.in_strip = len(self.stack) + 1
        parent = self.stack[-1] if self.stack else (None, {})
        if tag == "span" and parent[0] == "button" and (
            "audience-btn" in (parent[1].get("class") or "") or self.in_strip
        ):
            self._current = [attrs, ""]
        self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "span" and self._current is not None:
            self.glyphs.append((self._current[1], self._current[0]))
            self._current = None
        if self.stack:
            self.stack.pop()
        if self.in_strip and len(self.stack) < self.in_strip:
            self.in_strip = 0

    def handle_data(self, data):
        if self._current is not None:
            self._current[1] += data


def test_decorative_glyphs_are_hidden_from_screen_readers():
    parser = _Glyphs()
    parser.feed(HOME)
    assert len(parser.glyphs) >= 8, parser.glyphs  # 5 profils + 3 parcours
    for text, attrs in parser.glyphs:
        assert attrs.get("aria-hidden") == "true", f"glyphe lu à voix haute : {text!r}"


def test_brand_in_page_text_is_not_translated():
    body = HOME[HOME.find("<body"):]
    visible = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    # Chaque « Teranga AI » du texte (hors attributs) est dans un élément translate="no".
    for match in re.finditer(r">([^<]*Teranga AI[^<]*)<", visible):
        before = visible[: match.start() + 1]
        opening = before[before.rfind("<"):]
        assert 'translate="no"' in opening, f"marque traduisible : {match.group(1)[:60]!r}"
