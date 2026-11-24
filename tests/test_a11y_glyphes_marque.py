"""Accueil : les glyphes décoratifs des boutons sont muets pour les lecteurs d'écran, la marque n'est pas traduite.

Audit V3 (règles d'interface de Vercel, 25 octobre 2026) :
- les symboles des boutons de profil (✦ ✈ ⌂ ↔ ◆) et des parcours (🌍 🇸🇳 ✦) étaient lus à voix haute (« avion »,
  « globe terrestre », « drapeau : Sénégal ») avant le vrai libellé du bouton : ils portent aria-hidden="true" ;
- « Teranga AI » dans le texte de la page pouvait être traduit par Chrome : il porte translate="no", comme l'en-tête.
Changement invisible à l'écran.
"""

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


class _BrandText(HTMLParser):
    """Relève chaque texte visible qui contient « Teranga AI », avec l'attribut translate de son élément."""

    VOID = {"meta", "link", "br", "img", "input", "hr", "source", "use", "path", "circle", "rect"}

    def __init__(self):
        super().__init__()
        self.stack = []  # (balise, translate)
        self.found = []  # (texte, protégé)

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append((tag, dict(attrs).get("translate")))

    def handle_endtag(self, tag):
        # Une balise vide (« <path … /> ») ou inconnue de la pile ne ferme rien.
        if tag in self.VOID or tag not in (t for t, _ in self.stack):
            return
        while self.stack:
            if self.stack.pop()[0] == tag:
                break

    def handle_data(self, data):
        tags = [t for t, _ in self.stack]
        if "Teranga AI" not in data or "body" not in tags or {"script", "style", "title"} & set(tags):
            return
        self.found.append((data.strip(), any(value == "no" for _, value in self.stack)))


def test_brand_in_page_text_is_not_translated():
    parser = _BrandText()
    parser.feed(HOME)
    assert parser.found, "aucun « Teranga AI » trouvé dans le texte de la page"
    for text, protected in parser.found:
        assert protected, f"marque traduisible : {text[:60]!r}"
